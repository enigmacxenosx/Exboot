$ErrorActionPreference = 'Stop'

Write-Host 'Preparing Exboot Windows build...'
python -m pip install --upgrade pyinstaller
if ($LASTEXITCODE -ne 0) { throw 'Could not install PyInstaller.' }

if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path dist) { Remove-Item dist -Recurse -Force }

python -m PyInstaller --noconfirm --clean --onefile --windowed --name Exboot exboot.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }

Write-Host 'Build complete: dist\Exboot.exe'
