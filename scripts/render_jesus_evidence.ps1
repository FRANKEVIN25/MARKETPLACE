Add-Type -AssemblyName System.Drawing
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$out = Join-Path $repo 'docs/evidence'
$color = {
    param([string]$hex)
    [System.Drawing.ColorTranslator]::FromHtml($hex)
}
$navy = & $color '#153354'
$muted = & $color '#536579'
$blue = & $color '#1374a6'
$green = & $color '#27824f'
$red = & $color '#ad3540'
$pale = & $color '#f2f7fb'
$line = & $color '#d8e2ed'
$fontTitle = New-Object System.Drawing.Font('Segoe UI', 26, [System.Drawing.FontStyle]::Bold)
$fontSub = New-Object System.Drawing.Font('Segoe UI', 14)
$fontHead = New-Object System.Drawing.Font('Segoe UI', 15, [System.Drawing.FontStyle]::Bold)
$fontBody = New-Object System.Drawing.Font('Segoe UI', 15)
$fontFoot = New-Object System.Drawing.Font('Segoe UI', 11)

function New-Canvas([string]$title, [string]$subtitle) {
    $bmp = New-Object System.Drawing.Bitmap 1600,700
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = 'AntiAlias'
    $g.TextRenderingHint = 'AntiAliasGridFit'
    $g.Clear([System.Drawing.Color]::White)
    $g.DrawString($title, $fontTitle, (New-Object System.Drawing.SolidBrush($navy)), 65, 45)
    $g.DrawString($subtitle, $fontSub, (New-Object System.Drawing.SolidBrush($muted)), 68, 105)
    return @{ Bmp = $bmp; G = $g }
}

function Draw-Text($g, [string]$s, $font, $colorValue, [int]$x, [int]$y) {
    $brush = New-Object System.Drawing.SolidBrush($colorValue)
    try { $g.DrawString($s, $font, $brush, $x, $y) } finally { $brush.Dispose() }
}

function Draw-Row($g, [int]$y, [string]$label, [string]$value) {
    $brush = New-Object System.Drawing.SolidBrush($pale)
    $g.FillRectangle($brush, 65, $y, 1470, 85)
    $brush.Dispose()
    Draw-Text $g $label $fontHead $navy 90 ($y + 22)
    Draw-Text $g $value $fontBody $navy 380 ($y + 22)
}

function Save-Canvas($canvas, [string]$file, [string]$footer) {
    Draw-Text $canvas.G $footer $fontFoot $muted 68 645
    $canvas.Bmp.Save((Join-Path $out $file), [System.Drawing.Imaging.ImageFormat]::Png)
    $canvas.G.Dispose()
    $canvas.Bmp.Dispose()
}

$c = New-Canvas 'Bloque 1 · Docker Compose' 'Resumen visual de las comprobaciones registradas · rama Kubernetes · commit base a923695'
Draw-Row $c.G 180 'Empresa A' '12 productos BENCH · stock 1 000 c/u · login, catálogo, pedido: pasó'
Draw-Row $c.G 280 'Empresa B' '12 productos BENCH · stock 1 000 c/u · login, catálogo, pedido: pasó'
Draw-Row $c.G 380 'Empresa C' '12 productos BENCH · stock 1 000 c/u · login, catálogo, pedido: pasó'
Draw-Row $c.G 480 'Conjunto' '8 módulos · aislamiento: pasó · seed repetido sin duplicar'
Save-Canvas $c 'jesus-bloque1.png' 'Fuente: docs/evidence/jesus-bloque1.json · prueba local del 22/11/2026'

$c = New-Canvas 'Bloque 2 · Un Pod en Minikube' 'Pruebas cortas independientes; no son una comparación de rendimiento'
Draw-Row $c.G 180 'Funcional' 'A, B y C: login, catálogo, stock, pedido y aislamiento pasaron'
Draw-Row $c.G 280 'Persistencia' 'Datos conservaron tras reemplazar Odoo y PostgreSQL'
Draw-Row $c.G 380 'Lectura' '5 usuarios · 30 s · 409 solicitudes · 0 fallos · p95 ≈ 14 ms'
Draw-Row $c.G 480 'Escritura' '1 usuario · 30 s · 80 solicitudes · 0 fallos · p95 ≈ 65 ms'
Save-Canvas $c 'jesus-bloque2.png' 'Un nodo · 4 CPU · 3 072 MB · fuente: docs/evidence/jesus-bloque2.json'

$b3 = Get-Content (Join-Path $out 'jesus-bloque3.json') -Raw | ConvertFrom-Json
$deleted = ([datetime]$b3.pod_deletion_during_read_load.deleted_at_utc).ToUniversalTime()
$infra = Import-Csv (Join-Path $repo 'docs/evidence/runs/202611222150154038/infrastructure.csv')
$points = @($infra | ForEach-Object {
    @{ Seconds = ([datetime]::Parse($_.timestamp_utc).ToUniversalTime() - $deleted).TotalSeconds; Ready = [int]$_.ready_replicas }
})
$c = New-Canvas 'Bloque 3 · Recuperación de dos réplicas' '20 usuarios · lectura durante 120 s · Pod eliminado en t = 0'
$g = $c.G
$plotLeft = 205; $plotTop = 200; $plotWidth = 1225; $plotHeight = 300
$xMin = -25; $xMax = 45
$xPos = { param($sec) [int]($plotLeft + ($sec - $xMin) / ($xMax - $xMin) * $plotWidth) }
$yPos = { param($ready) [int]($plotTop + $plotHeight - ($ready - 0.75) / 1.5 * $plotHeight) }
$axisPen = New-Object System.Drawing.Pen($line, 2)
$bluePen = New-Object System.Drawing.Pen($blue, 5)
$redPen = New-Object System.Drawing.Pen($red, 3)
$greenPen = New-Object System.Drawing.Pen($green, 3)
$g.DrawLine($axisPen, $plotLeft, (& $yPos 1), ($plotLeft + $plotWidth), (& $yPos 1))
$g.DrawLine($axisPen, $plotLeft, (& $yPos 2), ($plotLeft + $plotWidth), (& $yPos 2))
Draw-Text $g '2 Pods listos' $fontSub $muted 10 ((& $yPos 2) - 15)
Draw-Text $g '1 Pod listo' $fontSub $muted 10 ((& $yPos 1) - 15)
for ($i = 1; $i -lt $points.Count; $i++) {
    $prev = $points[$i - 1]; $curr = $points[$i]
    $g.DrawLine($bluePen, (& $xPos $prev.Seconds), (& $yPos $prev.Ready), (& $xPos $curr.Seconds), (& $yPos $prev.Ready))
    $g.DrawLine($bluePen, (& $xPos $curr.Seconds), (& $yPos $prev.Ready), (& $xPos $curr.Seconds), (& $yPos $curr.Ready))
}
$g.DrawLine($redPen, (& $xPos 0), $plotTop, (& $xPos 0), ($plotTop + $plotHeight))
$g.DrawLine($greenPen, (& $xPos 13.246), $plotTop, (& $xPos 13.246), ($plotTop + $plotHeight))
foreach ($tick in @(-20, -10, 0, 10, 20, 30, 40)) {
    Draw-Text $g ($tick.ToString()) $fontSub $muted ((& $xPos $tick) - 12) 510
}
Draw-Text $g 'Segundos desde la eliminación del Pod' $fontSub $muted 600 550
Draw-Text $g 'Rojo: eliminación  ·  Verde: 2 Pods listos en 13,25 s' $fontBody $navy 150 585
Draw-Text $g '6 978 solicitudes  ·  3 fallos a los ~4 s (0,043 %)' $fontBody $navy 845 585
Save-Canvas $c 'jesus-bloque3.png' 'Recuperación cronometrada por sondeo; serie visual muestreada cada ~6 s · un solo nodo · fuente: jesus-bloque3.json'
$axisPen.Dispose(); $bluePen.Dispose(); $redPen.Dispose(); $greenPen.Dispose()
