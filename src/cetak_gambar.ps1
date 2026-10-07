# Cetak gambar (PNG) ke printer lewat driver Windows, 1 gambar = 1 halaman, pada kertas
# berukuran tetap (mm). Dipakai print_spesial.py --jenis lazada (tanpa SumatraPDF): gambar
# sudah dirender pada skala custom 68% dengan resolusi SAMA dengan printer (-Dpi), di sini
# hanya ditempel di pojok kiri-atas kertas (rata tengah horizontal) 1 piksel = 1 dot, tanpa skala lagi.
# Pemakaian: powershell -File cetak_gambar.ps1 -Printer NAMA -Dpi 300 -Gambar a.png,b.png
#            [-LebarMm 100 -TinggiMm 150] [-KeFile hasil.pdf  (uji: printer "Print to PDF")]
param(
    [Parameter(Mandatory = $true)][string]$Printer,
    [Parameter(Mandatory = $true)][string[]]$Gambar,
    [int]$Dpi = 300,
    [double]$LebarMm = 100,
    [double]$TinggiMm = 150,
    [string]$KeFile = ""
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$lebar100 = [int][math]::Round($LebarMm / 25.4 * 100)      # 1/100 inci
$tinggi100 = [int][math]::Round($TinggiMm / 25.4 * 100)
# lewat -File, daftar "a.png,b.png" tiba sebagai 1 string: pecah
$berkas = @($Gambar | ForEach-Object { $_ -split ',' } | Where-Object { $_ })
$daftarGambar = @($berkas | ForEach-Object { [System.Drawing.Image]::FromFile($_) })
$script:i = 0

$pd = New-Object System.Drawing.Printing.PrintDocument
$pd.PrinterSettings.PrinterName = $Printer
if (-not $pd.PrinterSettings.IsValid) { throw "Printer tidak valid: $Printer" }
if ($KeFile) { $pd.PrinterSettings.PrintToFile = $true; $pd.PrinterSettings.PrintFileName = $KeFile }
$pd.DocumentName = [System.IO.Path]::GetFileName($berkas[0])
$pd.OriginAtMargins = $false
$pd.DefaultPageSettings.Margins = New-Object System.Drawing.Printing.Margins(0, 0, 0, 0)
$pd.DefaultPageSettings.Landscape = $false

# pakai ukuran kertas yang sudah ada di printer kalau cocok (+-3/100 inci), kalau tidak ukuran custom
$kertas = $null
foreach ($k in $pd.PrinterSettings.PaperSizes) {
    if ([math]::Abs($k.Width - $lebar100) -le 3 -and [math]::Abs($k.Height - $tinggi100) -le 3) { $kertas = $k; break }
}
if (-not $kertas) { $kertas = New-Object System.Drawing.Printing.PaperSize("Label", $lebar100, $tinggi100) }
$pd.DefaultPageSettings.PaperSize = $kertas

$lebarPx = [int][math]::Round($LebarMm / 25.4 * $Dpi)      # kertas dalam dot printer
$pd.add_PrintPage({
    param($sender, $e)
    $g = $e.Graphics
    $g.PageUnit = [System.Drawing.GraphicsUnit]::Pixel         # 1 unit = 1 dot printer
    # asal koordinat GDI+ = pojok area cetak; geser ke pojok fisik kertas (HardMargin: 1/100 inci)
    $g.TranslateTransform(-$e.PageSettings.HardMarginX / 100 * $Dpi, -$e.PageSettings.HardMarginY / 100 * $Dpi)
    $img = $daftarGambar[$script:i]
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
    $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::Half
    $x = [math]::Floor(($lebarPx - $img.Width) / 2)
    $g.DrawImage($img, [int]$x, 0, $img.Width, $img.Height)   # ukuran asli: 1 piksel gambar = 1 dot
    $script:i++
    $e.HasMorePages = ($script:i -lt $daftarGambar.Count)
})
$pd.Print()
$daftarGambar | ForEach-Object { $_.Dispose() }
