$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $PSCommandPath
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")

Push-Location $repoRoot
try {
    python -m PyInstaller --clean --noconfirm windows_app/SuperLibraryMachine-win.spec
    Write-Host "Windows build created under dist\\SuperLibraryMachine" -ForegroundColor Green
}
finally {
    Pop-Location
}
