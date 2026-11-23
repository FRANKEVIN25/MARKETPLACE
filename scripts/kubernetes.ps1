param(
    [ValidateSet('Install', 'Up', 'Status', 'Forward', 'Check', 'Stop')]
    [string]$Action = 'Up',
    [ValidatePattern('^ecomparts-k8s(?:-[a-z0-9-]+)?$')]
    [string]$ClusterProfile = 'ecomparts-k8s',
    [ValidateRange(1024, 65535)]
    [int]$LocalPort = 18070,
    [ValidateRange(2, 8)]
    [int]$Cpus = 4,
    [ValidateRange(3072, 16384)]
    [int]$MemoryMb = 4096,
    [switch]$Seed
)

$ErrorActionPreference = 'Stop'
$repoPath = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $repoPath
$toolsPath = Join-Path $repoPath '.tools'
$statePath = Join-Path $repoPath '.lab'
$minikubePath = Join-Path $toolsPath 'minikube.exe'
$kubectlPath = Join-Path $toolsPath 'kubectl.exe'
$secretEnvPath = Join-Path $repoPath '.env.k8s'
$forwardStatePath = Join-Path $statePath ($ClusterProfile + '-forward.json')
$kubernetesVersion = 'v1.37.0'
$previousMinikubeHome = $env:MINIKUBE_HOME
$previousKubeconfig = $env:KUBECONFIG
New-Item -ItemType Directory -Path $toolsPath, $statePath -Force | Out-Null
$env:MINIKUBE_HOME = Join-Path $statePath '.minikube'
$env:KUBECONFIG = Join-Path $statePath 'kubeconfig'

function Invoke-Native([string]$File, [string[]]$CommandArgs, [switch]$Capture) {
    $savedPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        if ($Capture) { $result = & $File @CommandArgs }
        else { & $File @CommandArgs }
        $nativeExitCode = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = $savedPreference }
    if ($nativeExitCode -ne 0) { throw "Fallo $([IO.Path]::GetFileName($File)): $($CommandArgs -join ' ')" }
    if ($Capture) { return $result }
}

function Invoke-Kube([string[]]$CommandArgs, [switch]$Capture) {
    $targetArgs = @('--context', $ClusterProfile, '--namespace', 'ecomparts') + $CommandArgs
    if ($Capture) { return Invoke-Native $kubectlPath $targetArgs -Capture }
    Invoke-Native $kubectlPath $targetArgs
}

function Save-Json([string]$Path, $Value) {
    [IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth 30) + "`n", [Text.UTF8Encoding]::new($false))
}

function Install-VerifiedBinary([string]$Name, [string]$Url) {
    $binaryPath = Join-Path $toolsPath $Name
    $checksumPath = $binaryPath + '.sha256'
    $savedProgress = $ProgressPreference
    try {
        $ProgressPreference = 'SilentlyContinue'
        if (-not (Test-Path -LiteralPath $checksumPath)) {
            Invoke-WebRequest -UseBasicParsing -Uri ($Url + '.sha256') -OutFile $checksumPath
        }
        if (-not (Test-Path -LiteralPath $binaryPath)) {
            Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile ($binaryPath + '.download')
            $downloadedHash = (Get-FileHash -LiteralPath ($binaryPath + '.download') -Algorithm SHA256).Hash
            $expectedHash = ((Get-Content -LiteralPath $checksumPath -Raw).Trim() -split '\s+')[0]
            if ($downloadedHash -ne $expectedHash) { throw "SHA256 incorrecto: $Name" }
            Move-Item -LiteralPath ($binaryPath + '.download') -Destination $binaryPath
        }
        $actualHash = (Get-FileHash -LiteralPath $binaryPath -Algorithm SHA256).Hash
        $expectedHash = ((Get-Content -LiteralPath $checksumPath -Raw).Trim() -split '\s+')[0]
        if ($actualHash -ne $expectedHash) { throw "SHA256 incorrecto: $Name" }
    }
    finally { $ProgressPreference = $savedProgress }
}

function Initialize-Secrets {
    if (-not (Test-Path -LiteralPath $secretEnvPath)) {
        $random = [Security.Cryptography.RandomNumberGenerator]::Create()
        $passwords = @{}
        foreach ($key in @('postgres', 'admin', 'service', 'master')) {
            $bytes = New-Object byte[] 32
            $random.GetBytes($bytes)
            $passwords[$key] = [Convert]::ToBase64String($bytes)
        }
        $random.Dispose()
        $lines = @(
            'LAB_MODE=1', 'ODOO_DB=ecomparts_odoo_shared', 'POSTGRES_USER=ecomparts_user',
            ('POSTGRES_PASSWORD=' + $passwords.postgres),
            'ODOO_ADMIN_LOGIN=admin2@ecomparts.local', ('ODOO_ADMIN_PASS=' + $passwords.admin),
            ('ODOO_ADMIN_PASSWORD=' + $passwords.master),
            'ODOO_SERVICE_LOGIN=service@ecomparts.local', ('ODOO_SERVICE_PASS=' + $passwords.service)
        )
        [IO.File]::WriteAllLines($secretEnvPath, $lines, [Text.UTF8Encoding]::new($false))
        Write-Host 'Creado .env.k8s con credenciales locales aleatorias.'
    }
    $secretJson = Invoke-Kube @('create', 'secret', 'generic', 'ecomparts-secrets', ('--from-env-file=' + $secretEnvPath), '--dry-run=client', '-o', 'json') -Capture
    $secretObject = ($secretJson -join "`n") | ConvertFrom-Json
    $secretObject.data.PSObject.Properties.Remove('LAB_MODE')
    $secretObject.data.PSObject.Properties.Remove('ODOO_DB')
    $secretManifestPath = Join-Path $statePath 'k8s-secret.json'
    Save-Json $secretManifestPath $secretObject
    Invoke-Kube @('apply', '-f', $secretManifestPath)
}

function Stop-Forward {
    if (-not (Test-Path -LiteralPath $forwardStatePath)) { return }
    $forwardState = Get-Content -LiteralPath $forwardStatePath -Raw | ConvertFrom-Json
    $forwardProcess = Get-Process -Id $forwardState.pid -ErrorAction SilentlyContinue
    if ($forwardProcess) {
        $savedStartUtc = ([DateTime]$forwardState.started_at_utc).ToUniversalTime().ToString('o')
        if ($forwardProcess.Path -ne $kubectlPath -or $forwardProcess.StartTime.ToUniversalTime().ToString('o') -ne $savedStartUtc) {
            throw 'El PID del tunel ya no corresponde al proceso creado por este laboratorio.'
        }
        Stop-Process -Id $forwardProcess.Id
        if (-not $forwardProcess.WaitForExit(5000)) { throw 'El tunel anterior no termino a tiempo.' }
    }
    Remove-Item -LiteralPath $forwardStatePath
}

function Start-Forward {
    Stop-Forward
    $forwardArgs = @('--context', $ClusterProfile, '--namespace', 'ecomparts', 'port-forward', 'service/odoo', ($LocalPort.ToString() + ':8069'), '--address', '127.0.0.1')
    $forwardProcess = Start-Process -FilePath $kubectlPath -ArgumentList $forwardArgs -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $statePath ($ClusterProfile + '-forward.log')) `
        -RedirectStandardError (Join-Path $statePath ($ClusterProfile + '-forward.err.log'))
    Save-Json $forwardStatePath @{
        pid = $forwardProcess.Id
        started_at_utc = $forwardProcess.StartTime.ToUniversalTime().ToString('o')
        profile = $ClusterProfile
        port = $LocalPort
    }
    for ($attempt = 0; $attempt -lt 15; $attempt++) {
        try {
            $health = Invoke-RestMethod -Uri ("http://127.0.0.1:$LocalPort/web/health?db_server_status=true") -TimeoutSec 3
            if ($health.status -eq 'pass') {
                Write-Host "Odoo disponible por el Service: http://127.0.0.1:$LocalPort"
                return
            }
        }
        catch { Start-Sleep -Seconds 2 }
    }
    throw 'El tunel al Service de Odoo no quedo disponible. Revisa .lab/*-forward.err.log.'
}

function Get-AppPod([string]$Name) {
    $podText = Invoke-Kube @('get', 'pods', '-l', ('app.kubernetes.io/name=' + $Name), '-o', 'json') -Capture
    $pods = (($podText -join "`n") | ConvertFrom-Json).items
    $activePods = @($pods | Where-Object { -not $_.metadata.deletionTimestamp })
    if ($activePods.Count -ne 1) { throw "El bloque 2 requiere exactamente un Pod activo de $Name." }
    return $activePods[0]
}

function Wait-AppPod([string]$Name) {
    $candidate = $null
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try { $candidate = Get-AppPod $Name; break }
        catch { Start-Sleep -Seconds 1 }
    }
    if (-not $candidate) { throw "No aparecio el Pod de reemplazo de $Name." }
    Invoke-Kube @('wait', '--for=condition=Ready', ('pod/' + $candidate.metadata.name), '--timeout=300s')
}

function Apply-ImageManifest([string]$Path, [string]$Container, [string]$Image) {
    $rendered = Invoke-Kube @('set', 'image', '--local', '-f', $Path, ($Container + '=' + $Image), '-o', 'json') -Capture
    $renderedPath = Join-Path $statePath ($Container + '-manifest.json')
    [IO.File]::WriteAllText($renderedPath, ($rendered -join "`n"), [Text.UTF8Encoding]::new($false))
    Invoke-Kube @('apply', '-f', $renderedPath)
}

try {
    Install-VerifiedBinary 'minikube.exe' 'https://github.com/kubernetes/minikube/releases/download/v1.39.0/minikube-windows-amd64.exe'
    Install-VerifiedBinary 'kubectl.exe' ('https://dl.k8s.io/release/' + $kubernetesVersion + '/bin/windows/amd64/kubectl.exe')
    switch ($Action) {
        'Install' {
            Invoke-Native $minikubePath @('version')
            Invoke-Native $kubectlPath @('version', '--client')
        }
        'Up' {
            Invoke-Native $minikubePath @('start', ('--profile=' + $ClusterProfile), '--driver=docker', '--container-runtime=containerd', ('--kubernetes-version=' + $kubernetesVersion), ('--cpus=' + $Cpus), ('--memory=' + $MemoryMb), '--wait=all', '--wait-timeout=6m')
            Invoke-Native $minikubePath @('addons', 'enable', 'metrics-server', '-p', $ClusterProfile)
            Invoke-Native 'docker' @('build', '--tag', 'ecomparts-odoo:block2', 'services/odoo')
            $imageId = (Invoke-Native 'docker' @('image', 'inspect', '--format', '{{.Id}}', 'ecomparts-odoo:block2') -Capture).Trim()
            $imageTag = 'ecomparts-odoo:block2-' + $imageId.Replace('sha256:', '').Substring(0, 12)
            Invoke-Native 'docker' @('tag', 'ecomparts-odoo:block2', $imageTag)
            Invoke-Native $minikubePath @('image', 'load', $imageTag, '--daemon=true', '-p', $ClusterProfile)
            Invoke-Native $minikubePath @('image', 'load', 'postgres:16-alpine', '--daemon=true', '-p', $ClusterProfile)
            Invoke-Kube @('apply', '-f', 'k8s/namespace.yaml')
            Initialize-Secrets
            Invoke-Kube @('apply', '-k', 'k8s/config')
            Invoke-Kube @('apply', '-k', 'k8s/infrastructure')
            Invoke-Kube @('rollout', 'status', 'statefulset/postgres', '--timeout=300s')
            Invoke-Kube @('delete', 'job', 'odoo-init', '--ignore-not-found=true', '--wait=true')
            Apply-ImageManifest 'k8s/jobs/odoo-init.yaml' 'odoo-init' $imageTag
            try { Invoke-Kube @('wait', '--for=condition=complete', 'job/odoo-init', '--timeout=600s') }
            catch {
                Invoke-Kube @('logs', 'job/odoo-init', '--tail=80')
                throw
            }
            $existingDeployment = Invoke-Kube @('get', 'deployment', 'odoo', '--ignore-not-found', '-o', 'name') -Capture
            Invoke-Kube @('apply', '-f', 'k8s/odoo/service.yaml')
            Apply-ImageManifest 'k8s/odoo/deployment.yaml' 'odoo' $imageTag
            if ($existingDeployment) { Invoke-Kube @('rollout', 'restart', 'deployment/odoo') }
            Invoke-Kube @('rollout', 'status', 'deployment/odoo', '--timeout=300s')
            Save-Json (Join-Path $statePath ($ClusterProfile + '-image.json')) @{ image = $imageTag; image_id = $imageId }
            Start-Forward
            Invoke-Kube @('get', 'pods,services,pvc')
        }
        'Forward' { Start-Forward }
        'Status' {
            Invoke-Kube @('get', 'pods,services,pvc')
            Invoke-Kube @('top', 'pods')
        }
        'Check' {
            Start-Forward
            $checkArgs = @('scripts/verify_odoo_lab.py', '--env-file', '.env.k8s', '--base-url', ("http://127.0.0.1:$LocalPort"), '--project', $ClusterProfile)
            if ($Seed) { $checkArgs += '--seed' }
            Invoke-Native 'python' $checkArgs
            $persistenceArgs = @('scripts/verify_kubernetes_persistence.py', '--profile', $ClusterProfile, '--base-url', ("http://127.0.0.1:$LocalPort"))
            Invoke-Native 'python' ($persistenceArgs + @('--action', 'create'))
            $beforeOdoo = Get-AppPod 'odoo'
            $beforePostgres = Get-AppPod 'postgres'
            $serviceBefore = ((Invoke-Kube @('get', 'service', 'odoo', '-o', 'json') -Capture) -join "`n") | ConvertFrom-Json
            Invoke-Kube @('delete', 'pod', $beforeOdoo.metadata.name, '--wait=true', '--timeout=90s')
            Wait-AppPod 'odoo'
            $afterOdoo = Get-AppPod 'odoo'
            if ($beforeOdoo.metadata.uid -eq $afterOdoo.metadata.uid) { throw 'El Pod de Odoo no fue reemplazado.' }
            Start-Forward
            Invoke-Native 'python' ($persistenceArgs + @('--action', 'check', '--stage', 'after_odoo_recreation'))
            Invoke-Kube @('delete', 'pod', $beforePostgres.metadata.name, '--wait=true', '--timeout=90s')
            Wait-AppPod 'postgres'
            Wait-AppPod 'odoo'
            $afterPostgres = Get-AppPod 'postgres'
            if ($beforePostgres.metadata.uid -eq $afterPostgres.metadata.uid) { throw 'El Pod de PostgreSQL no fue reemplazado.' }
            Start-Forward
            Invoke-Native 'python' ($persistenceArgs + @('--action', 'check', '--stage', 'after_postgres_recreation'))
            $serviceAfter = ((Invoke-Kube @('get', 'service', 'odoo', '-o', 'json') -Capture) -join "`n") | ConvertFrom-Json
            if ($serviceBefore.metadata.uid -ne $serviceAfter.metadata.uid) { throw 'El Service de Odoo cambio durante la prueba.' }
            $appPod = Get-AppPod 'odoo'
            $postgresPod = Get-AppPod 'postgres'
            $metrics = $null
            $metricObjects = @()
            for ($attempt = 0; $attempt -lt 15; $attempt++) {
                try {
                    $freshMetrics = @()
                    foreach ($measuredPod in @($appPod, $postgresPod)) {
                        $metricPath = '/apis/metrics.k8s.io/v1beta1/namespaces/ecomparts/pods/' + $measuredPod.metadata.name
                        $metric = ((Invoke-Kube @('get', '--raw', $metricPath) -Capture) -join "`n") | ConvertFrom-Json
                        if ([DateTime]$metric.timestamp -lt [DateTime]$measuredPod.metadata.creationTimestamp) {
                            throw 'La muestra de metricas es anterior al Pod de reemplazo.'
                        }
                        $freshMetrics += $metric
                    }
                    $metricObjects = $freshMetrics
                    $metrics = @()
                    foreach ($measuredPod in @($appPod, $postgresPod)) {
                        $metrics += Invoke-Kube @('top', 'pod', $measuredPod.metadata.name, '--no-headers') -Capture
                    }
                    break
                }
                catch { Start-Sleep -Seconds 5 }
            }
            if (-not $metrics) { throw 'No se recibieron metricas de CPU y RAM.' }
            $pvc = ((Invoke-Kube @('get', 'pvc', '-o', 'json') -Capture) -join "`n") | ConvertFrom-Json
            $evidence = [ordered]@{
                profile = $ClusterProfile
                checked_at_utc = [DateTime]::UtcNow.ToString('o')
                kubernetes_version = $kubernetesVersion
                odoo_replicas = 1
                workers_per_pod = 2
                cron_threads = 0
                image = (Get-Content -LiteralPath (Join-Path $statePath ($ClusterProfile + '-image.json')) -Raw | ConvertFrom-Json)
                service = @{ uid = $serviceAfter.metadata.uid; cluster_ip = $serviceAfter.spec.clusterIP; name = 'odoo'; namespace = 'ecomparts' }
                odoo_pod = @{ before_uid = $beforeOdoo.metadata.uid; after_uid = $afterOdoo.metadata.uid; resources = $appPod.spec.containers[0].resources }
                postgres_pod = @{ before_uid = $beforePostgres.metadata.uid; after_uid = $afterPostgres.metadata.uid; resources = $postgresPod.spec.containers[0].resources }
                pvc = @($pvc.items | ForEach-Object { @{ name = $_.metadata.name; phase = $_.status.phase; capacity = $_.status.capacity.storage; volume = $_.spec.volumeName } })
                observed_pod_metrics = @($metrics)
                observed_resource_metrics = $metricObjects
                functional_checks = (Get-Content -LiteralPath (Join-Path $statePath ($ClusterProfile + '-checks.json')) -Raw | ConvertFrom-Json)
                persistence = (Get-Content -LiteralPath (Join-Path $statePath ($ClusterProfile + '-persistence.json')) -Raw | ConvertFrom-Json)
                status = 'passed'
            }
            Save-Json (Join-Path $statePath ($ClusterProfile + '-evidence.json')) $evidence
            $metrics | Write-Host
            Write-Host ('Bloque 2 validado. Evidencia: .lab/' + $ClusterProfile + '-evidence.json')
        }
        'Stop' {
            Stop-Forward
            Invoke-Native $minikubePath @('stop', '-p', $ClusterProfile)
        }
    }
}
finally {
    $env:MINIKUBE_HOME = $previousMinikubeHome
    $env:KUBECONFIG = $previousKubeconfig
}
