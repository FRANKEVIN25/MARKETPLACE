param(
    [ValidateSet('Init', 'Up', 'Check', 'Status', 'Stop')]
    [string]$Action = 'Up',
    [ValidatePattern('^ecomparts-lab(?:-[a-z0-9-]+)?$')]
    [string]$ProjectName = 'ecomparts-lab',
    [switch]$Marketplace,
    [switch]$Seed
)

$ErrorActionPreference = 'Stop'
$repoPath = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $repoPath
$envPath = Join-Path $repoPath '.env.lab'

if (-not (Test-Path -LiteralPath $envPath)) {
    $random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $passwords = @{}
    foreach ($key in @('postgres', 'admin', 'service', 'master', 'django')) {
        $bytes = New-Object byte[] 32
        $random.GetBytes($bytes)
        $passwords[$key] = [Convert]::ToBase64String($bytes)
    }
    $random.Dispose()
    $lines = @(
        'LAB_MODE=1', 'COMPOSE_PROJECT_NAME=ecomparts-lab',
        'POSTGRES_USER=ecomparts_user', ('POSTGRES_PASSWORD=' + $passwords.postgres), 'POSTGRES_DB=postgres',
        'DJANGO_DB_NAME=ecomparts_marketplace', 'DJANGO_DB_USER=ecomparts_user', ('DJANGO_DB_PASSWORD=' + $passwords.postgres),
        'DJANGO_DB_HOST=postgres', 'DJANGO_DB_PORT=5432', ('DJANGO_SECRET_KEY=' + $passwords.django),
        'DJANGO_DEBUG=True', 'DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,backend', 'DJANGO_PORT=8001',
        'ODOO_IMAGE=ecomparts-odoo:lab', 'ODOO_DB=ecomparts_odoo_shared', 'ODOO_URL=http://odoo:8069',
        'ODOO_PORT=8070', 'ODOO_GEVENT_PORT=8072',
        'ODOO_ADMIN_LOGIN=admin2@ecomparts.local', ('ODOO_ADMIN_PASS=' + $passwords.admin), ('ODOO_ADMIN_PASSWORD=' + $passwords.master),
        'ODOO_SERVICE_LOGIN=service@ecomparts.local', ('ODOO_SERVICE_PASS=' + $passwords.service),
        'ODOO_USERNAME=service@ecomparts.local', ('ODOO_PASSWORD=' + $passwords.service),
        'REDIS_HOST=redis', 'REDIS_PORT=6379', 'CELERY_BROKER_URL=redis://redis:6379/0', 'CELERY_RESULT_BACKEND=redis://redis:6379/0',
        'CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000',
        'TIMEZONE=America/Lima', 'LANGUAGE_CODE=es-pe', 'COUNTRY_CODE=PE',
        'CLOUDINARY_CLOUD_NAME=', 'CLOUDINARY_API_KEY=', 'CLOUDINARY_API_SECRET=', 'FLOWER_PORT=5556'
    )
    [System.IO.File]::WriteAllLines($envPath, $lines, [System.Text.UTF8Encoding]::new($false))
    Write-Host 'Creado .env.lab con credenciales locales aleatorias.'
}

$composeArgs = @('compose', '--env-file', '.env.lab', '-p', $ProjectName, '-f', 'docker-compose.yml', '-f', 'compose.lab.yml')
function Invoke-LabCompose([string[]]$CommandArgs) {
    $previousPreference = $ErrorActionPreference
    try {
        # Docker escribe el progreso en stderr incluso cuando termina correctamente.
        $ErrorActionPreference = 'Continue'
        & docker @composeArgs @CommandArgs
        $composeExitCode = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = $previousPreference }
    if ($composeExitCode -ne 0) { throw "Docker Compose fallo: $($CommandArgs -join ' ')" }
}

Invoke-LabCompose @('config', '--quiet')
switch ($Action) {
    'Init' { Write-Host 'Configuracion de laboratorio preparada.' }
    'Up' {
        Invoke-LabCompose @('build', 'odoo')
        $targets = @('odoo')
        if ($Marketplace) {
            Invoke-LabCompose @('build', 'backend', 'celery_worker', 'celery_beat', 'flower')
            $targets += @('backend', 'celery_worker', 'celery_beat', 'flower')
        }
        Invoke-LabCompose (@('up', '-d', '--wait', '--wait-timeout', '600') + $targets)
        Invoke-LabCompose @('ps', '-a')
    }
    'Check' {
        $checkArgs = @('scripts/verify_odoo_lab.py', '--project', $ProjectName)
        if ($Seed) { $checkArgs += '--seed' }
        & python @checkArgs
        if ($LASTEXITCODE -ne 0) { throw 'Fallo la validacion de Odoo.' }
    }
    'Status' { Invoke-LabCompose @('ps', '-a') }
    'Stop' { Invoke-LabCompose @('down') }
}
