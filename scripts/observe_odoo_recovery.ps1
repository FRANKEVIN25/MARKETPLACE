param(
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9]+$')][string]$RunId,
    [ValidateRange(1, 500)][int]$Users = 20
)

# Run beside run_benchmark.ps1, only for the two-replica availability exercise.
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $repo
$kubectl = Join-Path $repo '.tools/kubectl.exe'
$base = @('--kubeconfig', (Join-Path $repo '.lab/kubeconfig'), '--context', 'ecomparts-k8s', '-n', 'ecomparts')
function Kube([string[]]$Arguments) {
    $output = & $kubectl @base @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'Fallo kubectl durante la prueba de recuperacion.' }
    return $output
}
function Json([string[]]$Arguments) { return ((Kube $Arguments) -join "`n") | ConvertFrom-Json }
function ReadyPods {
    return @((Json @('get', 'pods', '-l', 'app.kubernetes.io/name=odoo', '-o', 'json')).items | Where-Object {
        -not $_.metadata.deletionTimestamp -and
        @($_.status.conditions | Where-Object { $_.type -eq 'Ready' -and $_.status -eq 'True' }).Count
    })
}
$runDir = Join-Path $repo ('.lab/runs/' + $RunId)
$metadata = Get-Content -LiteralPath (Join-Path $runDir 'metadata.json') -Raw | ConvertFrom-Json
if ($metadata.mode -ne 'read' -or $metadata.hpa -or $metadata.pods_expected -ne 2 -or $metadata.users -ne $Users) {
    throw 'Se requiere una corrida de lectura con dos replicas fijas y los usuarios indicados.'
}
if ($metadata.finished_at_utc) { throw 'La corrida ya termino.' }
$job = 'bench-' + $RunId
$deadline = (Get-Date).AddSeconds(90)
$loadSample = $null
while ((Get-Date) -lt $deadline) {
    $jobPods = (Json @('get', 'pods', '-l', ('batch.kubernetes.io/job-name=' + $job), '-o', 'json')).items
    if (@($jobPods).Count -eq 1 -and $jobPods[0].status.phase -eq 'Running') {
        try { $history = Kube @('exec', $jobPods[0].metadata.name, '--', 'cat', '/results/run_stats_history.csv') }
        catch { $history = @() }
        $sample = @(($history -join "`n") | ConvertFrom-Csv | Where-Object Name -eq 'Aggregated') | Select-Object -Last 1
        $measuring = $true
        if ($metadata.protocol_version -ge 2) {
            try {
                $phase = ((Kube @('exec', $jobPods[0].metadata.name, '--', 'cat', '/results/phase.json')) -join "`n") | ConvertFrom-Json
                $measurementPhase = @($phase.phases | Where-Object phase -eq 'measurement') | Select-Object -Last 1
                $measuring = $phase.phase -eq 'measurement' -and $measurementPhase -and $sample -and
                    [double]$sample.Timestamp -ge ([DateTimeOffset]::Parse($measurementPhase.at_utc).ToUnixTimeSeconds() + 1)
            }
            catch { $measuring = $false }
        }
        if ($measuring -and $sample -and [int]$sample.'User Count' -eq $Users -and [int]$sample.'Total Request Count' -ge 100) {
            $loadSample = $sample
            $loadPod = $jobPods[0].metadata.name
            break
        }
    }
    Start-Sleep -Seconds 2
}
if (-not $loadSample) { throw 'No se confirmo carga efectiva antes del plazo; no se elimina ningun Pod.' }
Kube @('exec', $loadPod, '--', 'test', '!', '-f', '/results/exit_code') | Out-Null
$deployment = Json @('get', 'deployment', 'odoo', '-o', 'json')
$hpas = Json @('get', 'hpa', '-o', 'json')
if ($deployment.spec.replicas -ne 2 -or @($hpas.items).Count) { throw 'El escenario ya no es de dos replicas fijas sin HPA.' }
$podsBefore = @(ReadyPods)
if ($podsBefore.Count -ne 2) { throw 'Se requieren dos Pods listos antes del fallo.' }
$serviceBefore = Json @('get', 'service', 'odoo', '-o', 'json')
$victim = @($podsBefore | Sort-Object { $_.metadata.name })[0]
$deletedAt = [DateTime]::UtcNow.ToString('o')
$clock = [Diagnostics.Stopwatch]::StartNew()
Kube @('delete', 'pod', $victim.metadata.name, '--wait=false') | Out-Host
$samples = @()
$restored = $false
while ($clock.Elapsed.TotalSeconds -lt 120) {
    $ready = @(ReadyPods)
    $samples += @{ timestamp_utc = [DateTime]::UtcNow.ToString('o'); ready_pods = @($ready | ForEach-Object { $_.metadata.name }) }
    if ($ready.Count -eq 2 -and @($ready | Where-Object { $_.metadata.uid -eq $victim.metadata.uid }).Count -eq 0) {
        $restored = $true
        break
    }
    Start-Sleep -Milliseconds 500
}
$clock.Stop()
$serviceAfter = Json @('get', 'service', 'odoo', '-o', 'json')
$evidence = @{
    run_id = $RunId; users = $Users; deleted_pod = $victim.metadata.name; deleted_uid = $victim.metadata.uid
    deletion_requested_at_utc = $deletedAt; two_ready_observed_at_utc = $(if ($restored) { $samples[-1].timestamp_utc } else { $null })
    recovery_seconds = [Math]::Round($clock.Elapsed.TotalSeconds, 3); restored = $restored
    measurement_scope = 'delete request to observation of two ready non-terminating Pods; polling every 500ms plus API latency'
    ready_before = @($podsBefore | ForEach-Object { $_.metadata.name })
    service_uid_before = $serviceBefore.metadata.uid; service_uid_after = $serviceAfter.metadata.uid
    effective_load_before_deletion = $loadSample; samples = $samples
}
$path = Join-Path $runDir 'recovery.json'
[IO.File]::WriteAllText($path, ($evidence | ConvertTo-Json -Depth 15) + "`n", [Text.UTF8Encoding]::new($false))
if (-not $restored -or $serviceBefore.metadata.uid -ne $serviceAfter.metadata.uid) { throw "No se completo la recuperacion: $path" }
Write-Host "Recuperacion registrada en $path"
