param(
    [switch]$PortableWithModels,
    [switch]$SkipInstaller
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& .\.venv\Scripts\python.exe -m pip install 'pyinstaller>=6,<7'
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller installation failed.' }
$versionLine = Select-String -LiteralPath 'version.py' -Pattern "APP_VERSION = '([^']+)'"
if (!$versionLine) { throw 'APP_VERSION was not found.' }
$appVersion = $versionLine.Matches[0].Groups[1].Value
$taskRelease = Join-Path $PSScriptRoot "releases\v$appVersion"
& .\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm --distpath $taskRelease YukiTranslator.spec
if ($LASTEXITCODE -ne 0) { throw 'Application build failed.' }
& .\.venv\Scripts\python.exe prepare_dist.py (Join-Path $taskRelease 'YukiTranslator')
if ($LASTEXITCODE -ne 0) { throw 'Distribution preparation failed.' }
if ($PortableWithModels) {
    & .\.venv\Scripts\python.exe bundle_models.py (Join-Path $taskRelease 'YukiTranslator')
    if ($LASTEXITCODE -ne 0) { throw 'Model bundling failed. Run models_setup.py first.' }
}
if (!$SkipInstaller) {
    $iscc = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (!$iscc) { throw 'Inno Setup 6 is required. Install it with: winget install JRSoftware.InnoSetup' }
    & $iscc "/DAppVersion=$appVersion" "/DSourceDir=$taskRelease\YukiTranslator" installer.iss
    if ($LASTEXITCODE -ne 0) { throw 'Installer build failed.' }
}
Write-Host "Ready: releases\v$appVersion\installer\YukiTranslator-Setup-v$appVersion.exe"
