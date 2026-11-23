param(
    [int]$PortA = 18071,
    [int]$PortB = 18072
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $repo
$kubectl = Join-Path $repo '.tools/kubectl.exe'
$env:KUBECONFIG = Join-Path $repo '.lab/kubeconfig'
$base = @('--context', 'ecomparts-k8s', '--namespace', 'ecomparts')
$json = & $kubectl @base get pods -l app.kubernetes.io/name=odoo -o json
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron consultar los Pods de Odoo.' }
$pods = @(($json | ConvertFrom-Json).items | Where-Object {
    -not $_.metadata.deletionTimestamp -and
    @($_.status.conditions | Where-Object { $_.type -eq 'Ready' -and $_.status -eq 'True' }).Count -gt 0
})
if ($pods.Count -ne 2) { throw "Se requieren exactamente dos Pods listos; hay $($pods.Count)." }
$names = @($pods | ForEach-Object { $_.metadata.name } | Sort-Object)
$processes = @()
try {
    foreach ($i in 0,1) {
        $port = @($PortA, $PortB)[$i]
        $arguments = $base + @('port-forward', ('pod/' + $names[$i]), ("${port}:8069"), '--address', '127.0.0.1')
        $processes += Start-Process -FilePath $kubectl -ArgumentList $arguments -PassThru -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $repo ".lab/replica-forward-$i.log") `
            -RedirectStandardError (Join-Path $repo ".lab/replica-forward-$i.err.log")
    }
    Start-Sleep -Seconds 3
    & python scripts/verify_odoo_replicas.py --pod-a $names[0] --pod-b $names[1] `
        --url-a "http://127.0.0.1:$PortA" --url-b "http://127.0.0.1:$PortB"
    if ($LASTEXITCODE -ne 0) { throw 'Fallo la comprobacion entre replicas.' }
}
finally {
    foreach ($process in $processes) {
        if (-not $process.HasExited) {
            Stop-Process -Id $process.Id
            $null = $process.WaitForExit(5000)
        }
    }
}
