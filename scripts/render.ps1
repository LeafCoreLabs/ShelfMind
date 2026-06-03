# Render CLI wrapper (adds installed binary to PATH on Windows)
$BinDir = "$env:USERPROFILE\.local\bin"
$Cli = "$BinDir\cli_v2.19.0.exe"

if (-not (Test-Path $Cli)) {
    Write-Host "Installing Render CLI..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
    $zip = "$env:TEMP\render-cli.zip"
    Invoke-WebRequest -Uri "https://github.com/render-oss/cli/releases/download/v2.19.0/cli_2.19.0_windows_amd64.zip" -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $BinDir -Force
}

if ($args.Count -eq 0) {
    & $Cli
} else {
    & $Cli @args
}
exit $LASTEXITCODE
