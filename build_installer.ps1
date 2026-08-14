$ErrorActionPreference = 'Stop'

Write-Host 'Building Exboot executable...'
& "$PSScriptRoot\build_windows.ps1"
if ($LASTEXITCODE -ne 0) { throw 'Executable build failed.' }

$isccCandidates = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) { $iscc = $command.Source }
}
if (-not $iscc) { throw 'Inno Setup 6 was not found. Install it from https://jrsoftware.org/isinfo.php.' }

Write-Host 'Building Exboot installer...'
& $iscc "$PSScriptRoot\installer.iss"
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed.' }

Write-Host 'Installer created in installer-output.'
