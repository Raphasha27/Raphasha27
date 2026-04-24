<#
.SYNOPSIS
    Registers the KirovHeartbeat scheduled task (self-elevates to Admin).
.DESCRIPTION
    Run this ONCE to set up the daily 08:00 heartbeat.
    Usage:  .\setup_heartbeat_task.ps1 -Token "ghp_xxxxxxxxxxxx"
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$Token
)

# ── Self-elevate if not admin ──────────────────────────────────────────────────
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
        ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Elevating to Administrator..." -ForegroundColor Yellow
    $args = "-ExecutionPolicy Bypass -File `"$PSCommandPath`" -Token `"$Token`""
    Start-Process powershell.exe -ArgumentList $args -Verb RunAs -Wait
    exit
}

# ── Paths ──────────────────────────────────────────────────────────────────────
$scriptDir  = Split-Path -Parent $PSCommandPath
$heartbeat  = Join-Path $scriptDir "triage_heartbeat.ps1"
$logsDir    = Join-Path (Split-Path -Parent $scriptDir) "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

# ── Persist the token as a user env variable ───────────────────────────────────
[System.Environment]::SetEnvironmentVariable("GITHUB_TOKEN", $Token, "User")
Write-Host "GITHUB_TOKEN saved to User environment variables." -ForegroundColor Green

# ── Build the action (pass the token explicitly for reliability) ───────────────
$psArgs = "-NonInteractive -ExecutionPolicy Bypass " +
          "-Command `"`$env:GITHUB_TOKEN='$Token'; & '$heartbeat'`""

$action   = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $psArgs
$trigger  = New-ScheduledTaskTrigger -Daily -At "08:00"
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -StartWhenAvailable `
    -RestartCount 1 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal `
    -UserId ([System.Environment]::UserName) `
    -LogonType Interactive `
    -RunLevel Highest

# ── Register ───────────────────────────────────────────────────────────────────
$params = @{
    TaskName    = "KirovHeartbeat"
    Action      = $action
    Trigger     = $trigger
    Settings    = $settings
    Principal   = $principal
    Description = "Kirov Dynamics daily CI health triage for Raphasha27"
    Force       = $true
}
Register-ScheduledTask @params | Out-Null

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Kirov Heartbeat task registered!" -ForegroundColor Cyan
Write-Host "  Runs daily at 08:00 SAST" -ForegroundColor Cyan
Write-Host "  Script: $heartbeat" -ForegroundColor Cyan
Write-Host "  Logs:   $logsDir" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  To run NOW:  Start-ScheduledTask -TaskName KirovHeartbeat" -ForegroundColor Yellow
Write-Host "  To remove:   Unregister-ScheduledTask -TaskName KirovHeartbeat -Confirm:`$false" -ForegroundColor DarkGray
Write-Host ""

# ── Offer to run immediately ───────────────────────────────────────────────────
$run = Read-Host "Run a health check right now? (Y/N)"
if ($run -match "^[Yy]") {
    Write-Host ""
    & $env:GITHUB_TOKEN=$Token; & $heartbeat
}
