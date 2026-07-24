# =====================================================================
# One-time setup: downloads Bootstrap, Bootstrap Icons, and Chart.js
# into static/ so the app no longer depends on jsdelivr.net at
# runtime. Run this once from PowerShell on a machine with normal
# internet access (your CSP only blocks the *browser* from loading
# these on the rendered page — it doesn't block you downloading them
# here).
#
# Run from anywhere; it writes relative to the script's own location,
# i.e. into src\bjk_athletes\static\...
# =====================================================================

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$staticRoot = Join-Path $root "..\static"

$cssDir   = Join-Path $staticRoot "css"
$jsDir    = Join-Path $staticRoot "js"
$fontsDir = Join-Path $cssDir "fonts"

New-Item -ItemType Directory -Force -Path $cssDir, $jsDir, $fontsDir | Out-Null

$downloads = @(
    @{ Url = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css";              Out = "$cssDir\bootstrap.min.css" },
    @{ Url = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js";          Out = "$jsDir\bootstrap.bundle.min.js" },
    @{ Url = "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css";      Out = "$cssDir\bootstrap-icons.min.css" },
    @{ Url = "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/fonts/bootstrap-icons.woff2";  Out = "$fontsDir\bootstrap-icons.woff2" },
    @{ Url = "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/fonts/bootstrap-icons.woff";   Out = "$fontsDir\bootstrap-icons.woff" },
    @{ Url = "https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js";                     Out = "$jsDir\chart.umd.min.js" }
)

foreach ($item in $downloads) {
    Write-Host "Downloading $($item.Url) ..."
    Invoke-WebRequest -Uri $item.Url -OutFile $item.Out
}

# bootstrap-icons.min.css references its fonts as a relative "./fonts/..."
# path (matches the fontsDir layout above), so no rewriting needed.

Write-Host ""
Write-Host "Done. Files written under: $staticRoot"
Write-Host "  css\bootstrap.min.css"
Write-Host "  css\bootstrap-icons.min.css"
Write-Host "  css\fonts\bootstrap-icons.woff2 (+ .woff)"
Write-Host "  js\bootstrap.bundle.min.js"
Write-Host "  js\chart.umd.min.js"
