# ShelfMind — fix build + redeploy API on Render via CLI
# Usage:
#   .\scripts\deploy-render-backend.ps1 login     # one-time auth
#   .\scripts\deploy-render-backend.ps1 push      # commit + push build fix
#   .\scripts\deploy-render-backend.ps1 deploy    # trigger redeploy + tail logs
#   .\scripts\deploy-render-backend.ps1 status    # list services + last deploy

param(
    [Parameter(Position = 0)]
    [ValidateSet("login", "push", "deploy", "status", "logs")]
    [string]$Action = "deploy",
    [string]$ServiceName = "shelfmind-api"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Render = Join-Path $Root "scripts\render.ps1"
Set-Location $Root

function Invoke-Render {
    param([string[]]$RenderArgs)
    & $Render @RenderArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Require-Auth {
    & $Render whoami -o text --confirm 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Not logged in. Run:" -ForegroundColor Yellow
        Write-Host "  .\scripts\deploy-render-backend.ps1 login" -ForegroundColor White
        exit 1
    }
}

function Get-ServiceId {
    $raw = & $Render services list -o json --confirm
    if ($LASTEXITCODE -ne 0) { Write-Error "Could not list services"; exit 1 }
    $json = $raw | ConvertFrom-Json
    foreach ($item in $json) {
        $name = if ($item.service) { $item.service.name } else { $item.name }
        $id = if ($item.service) { $item.service.id } else { $item.id }
        if ($name -eq $ServiceName) { return $id }
    }
    Write-Error "Service '$ServiceName' not found. Check Render dashboard name."
}

switch ($Action) {
    "login" {
        & $Render login
        & $Render workspace set
        & $Render whoami -o text --confirm
    }
    "push" {
        Write-Host "Staging deploy fixes..." -ForegroundColor Cyan
        git add backend/Dockerfile backend/requirements-render.txt `
            backend/entrypoint.sh backend/app/config.py `
            backend/app/services/s3_reports.py backend/app/services/system_health.py `
            backend/app/api/routes/store/reports.py backend/app/tasks/forecast_tasks.py `
            render.yaml render-backend.yaml `
            scripts/render.ps1 scripts/deploy-render-backend.ps1 `
            DEPLOY_BACKEND_FREE.md DEPLOY_RENDER.md .env.example
        git diff --cached --quiet
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Nothing new to commit." -ForegroundColor Yellow
        } else {
            git commit -m "Fix Render free-tier Docker build and add CLI deploy scripts"
        }
        git push origin main
        Write-Host "Pushed to GitHub. Run deploy next." -ForegroundColor Green
    }
    "status" {
        Require-Auth
        & $Render services list -o text --confirm
        $id = Get-ServiceId
        & $Render deploys list $id -o text --confirm
    }
    "logs" {
        Require-Auth
        $id = Get-ServiceId
        & $Render logs $id --tail --confirm
    }
    "deploy" {
        Require-Auth
        & $Render blueprints validate render-backend.yaml
        $id = Get-ServiceId
        Write-Host "Redeploying $ServiceName ($id)..." -ForegroundColor Cyan
        & $Render deploys create $id --wait -o json --confirm
        Write-Host "Done. Health check:" -ForegroundColor Green
        Write-Host "  https://$ServiceName.onrender.com/api/health"
    }
}
