$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& .\.venv\Scripts\python.exe -m pip install 'pyinstaller>=6,<7'
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller installation failed.' }
$taskRelease = Join-Path $PSScriptRoot 'releases\studio-v6'
& .\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm --distpath $taskRelease YukiTranslator.spec
if ($LASTEXITCODE -ne 0) { throw 'Application build failed.' }
& .\.venv\Scripts\python.exe bundle_models.py (Join-Path $taskRelease 'YukiTranslator')
if ($LASTEXITCODE -ne 0) { throw 'Model bundling failed. Run models_setup.py first.' }
Write-Host 'Ready: releases\studio-v6\YukiTranslator\YukiTranslator.exe'
