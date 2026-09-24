# Creates a Start-menu "OKF Viewer" shortcut that launches OKF Server
# (`okf-gui serve`, ADR-0008) and lets it open the viewer itself. Idempotent:
# regenerates the icon and overwrites the shortcut on every run. Windows only;
# called from install.sh, safe to run standalone.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$okfDir = Join-Path $env:USERPROFILE '.okf'
$icoPath = Join-Path $okfDir 'viz.ico'

# okf-gui.exe is the windowed (pythonw) stub for `okf.cli:main` — launching it
# directly means no console window flashes when the shortcut is double-clicked.
$repoRoot = Split-Path $PSScriptRoot -Parent
$okfGuiExe = Join-Path $repoRoot '.venv\Scripts\okf-gui.exe'
if (-not (Test-Path $okfGuiExe)) {
    Write-Output "warn: $okfGuiExe not found (run pip install -e . first); skipping OKF Viewer shortcut"
    exit 0
}

# --- Draw the icon: three colored nodes joined by edges, on the viewer's
#     dark background. Written as a single 256px PNG-in-ICO (Vista+). ---
New-Item -ItemType Directory -Force $okfDir | Out-Null
$size = 256
$bmp = New-Object System.Drawing.Bitmap $size, $size
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = 'AntiAlias'
$g.Clear([System.Drawing.Color]::FromArgb(255, 30, 30, 46))

$edgePen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255, 120, 120, 150)), 10
$p1 = New-Object System.Drawing.Point 70, 80
$p2 = New-Object System.Drawing.Point 186, 70
$p3 = New-Object System.Drawing.Point 128, 190
$g.DrawLine($edgePen, $p1, $p2)
$g.DrawLine($edgePen, $p1, $p3)
$g.DrawLine($edgePen, $p2, $p3)

function Draw-Node($g, $cx, $cy, $r, $color) {
    $brush = New-Object System.Drawing.SolidBrush $color
    $g.FillEllipse($brush, $cx - $r, $cy - $r, 2 * $r, 2 * $r)
    $brush.Dispose()
}
Draw-Node $g 70 80 36 ([System.Drawing.Color]::FromArgb(255, 137, 180, 250))
Draw-Node $g 186 70 30 ([System.Drawing.Color]::FromArgb(255, 166, 227, 161))
Draw-Node $g 128 190 33 ([System.Drawing.Color]::FromArgb(255, 250, 179, 135))
$g.Dispose()

$ms = New-Object System.IO.MemoryStream
$bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
$png = $ms.ToArray()
$ms.Dispose(); $bmp.Dispose()

$fs = [System.IO.File]::Create($icoPath)
$bw = New-Object System.IO.BinaryWriter $fs
$bw.Write([uint16]0)      # reserved
$bw.Write([uint16]1)      # type: icon
$bw.Write([uint16]1)      # image count
$bw.Write([byte]0)        # width 256 -> 0
$bw.Write([byte]0)        # height 256 -> 0
$bw.Write([byte]0)        # palette
$bw.Write([byte]0)        # reserved
$bw.Write([uint16]1)      # planes
$bw.Write([uint16]32)     # bpp
$bw.Write([uint32]$png.Length)
$bw.Write([uint32]22)     # data offset (6-byte header + 16-byte entry)
$bw.Write($png)
$bw.Dispose(); $fs.Dispose()

# --- Start-menu shortcut (user scope, no elevation needed) ---
$lnkPath = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\OKF Viewer.lnk'

$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut($lnkPath)
$lnk.TargetPath = $okfGuiExe
$lnk.Arguments = 'serve'
$lnk.IconLocation = "$icoPath,0"
$lnk.Description = 'OKF Multi-KS notebook: start OKF Server and open the viewer'
$lnk.WorkingDirectory = $okfDir
$lnk.Save()

Write-Output "installed OKF Viewer shortcut -> $lnkPath (okf-gui.exe serve)"
