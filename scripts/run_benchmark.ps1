param(
    [ValidateSet('read', 'write')][string]$Mode = 'read',
    [ValidateRange(1, 500)][int]$Users = 20,
    [ValidateRange(1, 3)][int]$Pods = 1,
    [ValidateRange(1, 20)][int]$Repeat = 1,
    [ValidateRange(30, 3600)][int]$DurationSeconds = 300,
    [ValidateRange(0, 600)][int]$WarmupSeconds = 30,
    [ValidateRange(1, 100)][int]$SpawnRate = 5,
    [int]$Seed = 2026,
    [ValidateSet('smoke', 'benchmark', 'hpa', 'availability')][string]$Purpose = 'smoke',
    [ValidatePattern('^[A-Za-z0-9_-]{1,80}$')][string]$ExperimentId = 'manual',
    [switch]$Hpa
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $repo
$arguments = @('scripts/benchmark_runner.py', '--mode', $Mode, '--users', "$Users", '--pods', "$Pods",
    '--repeat', "$Repeat", '--duration-seconds', "$DurationSeconds", '--warmup-seconds', "$WarmupSeconds",
    '--spawn-rate', "$SpawnRate", '--seed', "$Seed", '--purpose', $Purpose, '--experiment-id', $ExperimentId)
if ($Hpa) { $arguments += '--hpa' }
& python @arguments
if ($LASTEXITCODE -ne 0) { throw 'La corrida no completo la validacion. Revisa su carpeta en .lab/runs.' }
