param(
    [ValidateSet('read', 'write')][string]$Mode = 'read',
    [ValidateRange(1, 500)][int]$Users = 20,
    [ValidateRange(1, 3)][int]$Pods = 1,
    [ValidateRange(1, 20)][int]$Repeat = 1,
    [ValidateRange(30, 3600)][int]$DurationSeconds = 300,
    [ValidateRange(1, 100)][int]$SpawnRate = 5,
    [switch]$Hpa
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $repo
$kubectl = Join-Path $repo '.tools/kubectl.exe'
if (-not (Test-Path -LiteralPath $kubectl)) { throw 'Ejecuta scripts/kubernetes.ps1 -Action Install primero.' }
$env:KUBECONFIG = Join-Path $repo '.lab/kubeconfig'
if (-not (Test-Path -LiteralPath $env:KUBECONFIG)) { throw 'Falta el kubeconfig del laboratorio.' }
$prefix = @('--context', 'ecomparts-k8s', '--namespace', 'ecomparts')
function Kube([string[]]$Arguments) {
    $output = & $kubectl @prefix @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) { throw ('kubectl ' + ($Arguments -join ' ') + ': ' + ($output -join ' ')) }
    return $output
}

$deployment = (Kube @('get', 'deployment', 'odoo', '-o', 'json') | Out-String) | ConvertFrom-Json
if (-not $Hpa -and ($deployment.spec.replicas -ne $Pods -or $deployment.status.readyReplicas -ne $Pods)) {
    throw "Se esperaban $Pods replicas listas; coordina la configuracion con Frank antes de medir."
}
if ($Hpa -and $deployment.status.readyReplicas -lt 1) { throw 'Odoo no tiene Pods listos.' }
$hpas = Kube @('get', 'hpa', '-o', 'json')
$hpaItems = (($hpas | Out-String) | ConvertFrom-Json).items
if (-not $Hpa -and $hpaItems.Count -gt 0) { throw 'Desactiva el HPA para comparar replicas fijas.' }
if ($Hpa -and $hpaItems.Count -eq 0) { throw 'Falta el HPA para esta prueba.' }

$runId = (Get-Date -Format 'yyyyMMddHHmmss') + (Get-Random -Minimum 1000 -Maximum 9999)
$jobName = "bench-$runId"
$runDir = Join-Path $repo (".lab/runs/$runId")
New-Item -ItemType Directory -Path $runDir -Force | Out-Null
$commit = (git rev-parse HEAD).Trim()
$configPath = Join-Path $runDir 'configmap.json'
$configJson = Kube @('create', 'configmap', 'benchmark-scripts',
    '--from-file=scripts/locustfile.py', '--from-file=scripts/verify_odoo_lab.py',
    '--dry-run=client', '-o', 'json')
[IO.File]::WriteAllText($configPath, ($configJson -join "`n"), [Text.UTF8Encoding]::new($false))
Kube @('apply', '-f', $configPath) | Out-Host

$locustArgs = @('-f', '/mnt/locust/locustfile.py', '--headless', '-H', 'http://odoo:8069',
          '-u', "$Users", '-r', "$SpawnRate", '-t', "${DurationSeconds}s",
          '--reset-stats', '--csv', '/results/run', '--csv-full-history',
          '--json-file', '/results/final',
          '--only-summary', '--exit-code-on-error', '0')
$locustCommand = 'locust ' + ($locustArgs -join ' ') +
    '; code=$?; printf "%s" "$code" > /results/exit_code; sleep 600'
$job = @{
    apiVersion = 'batch/v1'; kind = 'Job'
    metadata = @{ name = $jobName; namespace = 'ecomparts' }
    spec = @{
        backoffLimit = 0
        template = @{
            metadata = @{ labels = @{ 'app.kubernetes.io/name' = 'benchmark-load' } }
            spec = @{
                restartPolicy = 'Never'
                containers = @(@{
                    name = 'locust'; image = 'locustio/locust:2.47.0'
                    command = @('sh', '-c'); args = @($locustCommand)
                    envFrom = @(@{ configMapRef = @{ name = 'odoo-config' } },
                                @{ secretRef = @{ name = 'ecomparts-secrets' } })
                    env = @(@{ name = 'BENCH_MODE'; value = $Mode },
                            @{ name = 'BENCH_RUN_ID'; value = $runId },
                            @{ name = 'BENCH_TIMING_FILE'; value = '/results/timing.json' })
                    resources = @{ requests = @{ cpu = '250m'; memory = '256Mi' };
                                   limits = @{ cpu = '1000m'; memory = '1Gi' } }
                    volumeMounts = @(@{ name = 'scripts'; mountPath = '/mnt/locust'; readOnly = $true },
                                     @{ name = 'results'; mountPath = '/results' })
                })
                volumes = @(@{ name = 'scripts'; configMap = @{ name = 'benchmark-scripts' } },
                            @{ name = 'results'; emptyDir = @{} })
            }
        }
    }
}
$jobPath = Join-Path $runDir 'job.json'
[IO.File]::WriteAllText($jobPath, ($job | ConvertTo-Json -Depth 30), [Text.UTF8Encoding]::new($false))
$metadata = [ordered]@{
    run_id = $runId; commit = $commit; mode = $Mode; users = $Users
    working_tree_status = @((git status --porcelain --untracked-files=all))
    locust_script_sha256 = (Get-FileHash -LiteralPath scripts/locustfile.py -Algorithm SHA256).Hash
    pods_expected = $(if ($Hpa) { 'HPA' } else { $Pods })
    repeat = $Repeat; spawn_rate = $SpawnRate; duration_seconds = $DurationSeconds
    hpa = [bool]$Hpa; started_at_utc = [DateTime]::UtcNow.ToString('o')
    locust_image = 'locustio/locust:2.47.0'
    company_weights = 'A:B:C = 1:2:3'; read_mix = 'catalogue:stock = 3:2'
}
$metadataPath = Join-Path $runDir 'metadata.json'
[IO.File]::WriteAllText($metadataPath, ($metadata | ConvertTo-Json -Depth 10), [Text.UTF8Encoding]::new($false))
Kube @('apply', '-f', $jobPath) | Out-Host
try {
    $deadline = (Get-Date).AddSeconds($DurationSeconds + 300)
    $samples = @()
    $pod = $null
    $finished = $false
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 5
        $state = (Kube @('get', 'job', $jobName, '-o', 'json') | Out-String) | ConvertFrom-Json
        $jobPods = (Kube @('get', 'pods', '-l', "batch.kubernetes.io/job-name=$jobName", '-o', 'json') | Out-String | ConvertFrom-Json).items
        if ($jobPods.Count -gt 0) { $pod = $jobPods[0].metadata.name }
        $replicas = (Kube @('get', 'deployment', 'odoo', '-o', 'json') | Out-String) | ConvertFrom-Json
        try { $top = Kube @('top', 'pods', '--no-headers') }
        catch { $top = @('metrics unavailable') }
        try {
            $connections = (Kube @('exec', 'statefulset/postgres', '--', 'psql',
                '-U', 'ecomparts_user', '-d', 'ecomparts_odoo_shared', '-tAc',
                "SELECT count(*) FROM pg_stat_activity WHERE datname = 'ecomparts_odoo_shared'") | Out-String).Trim()
        }
        catch { $connections = 'unavailable' }
        $samples += [pscustomobject]@{
            timestamp_utc = [DateTime]::UtcNow.ToString('o')
            desired_replicas = $replicas.spec.replicas
            ready_replicas = $replicas.status.readyReplicas
            postgres_connections = $connections
            pod_metrics = ($top -join ' | ')
        }
        if ($pod) {
            try {
                Kube @('exec', $pod, '--', 'test', '-f', '/results/exit_code') | Out-Null
                $finished = $true
            }
            catch { }
        }
        if ($finished -or $state.status.failed -ge 1) { break }
    }
    $samples | Export-Csv -LiteralPath (Join-Path $runDir 'infrastructure.csv') -NoTypeInformation
    if (-not $pod -or -not $finished) { throw 'Locust no termino dentro del plazo. Revisa el Job.' }
    $exitCode = (Kube @('exec', $pod, '--', 'cat', '/results/exit_code') | Out-String).Trim()
    Kube @('logs', $pod) | Set-Content -LiteralPath (Join-Path $runDir 'locust.log')
    foreach ($suffix in @('stats', 'stats_history', 'failures', 'exceptions')) {
        $content = Kube @('exec', $pod, '--', 'cat', "/results/run_${suffix}.csv")
        [IO.File]::WriteAllText((Join-Path $runDir ("run_$suffix.csv")),
            ($content -join "`n") + "`n", [Text.UTF8Encoding]::new($false))
    }
    foreach ($filename in @('final.json', 'timing.json')) {
        $content = Kube @('exec', $pod, '--', 'cat', "/results/$filename")
        [IO.File]::WriteAllText((Join-Path $runDir $filename),
            ($content -join "`n") + "`n", [Text.UTF8Encoding]::new($false))
    }
    $metadata['finished_at_utc'] = [DateTime]::UtcNow.ToString('o')
    $metadata['locust_exit_code'] = $exitCode
    $metadata['job_succeeded'] = ($exitCode -eq '0')
    [IO.File]::WriteAllText($metadataPath, ($metadata | ConvertTo-Json -Depth 10), [Text.UTF8Encoding]::new($false))
    if (-not $metadata['job_succeeded']) { throw "Fallo Locust. Revisa $runDir/locust.log" }
    Write-Host "Corrida guardada en $runDir"
}
finally {
    Kube @('delete', 'job', $jobName, '--ignore-not-found=true') | Out-Host
}
