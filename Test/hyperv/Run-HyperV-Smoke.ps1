#Requires -RunAsAdministrator
#Requires -Version 5.1
<#
.SYNOPSIS
  AlmaLinux 10 Hyper-V smoke via Vagrant (recommended path on Windows).

.EXAMPLE
  cd Test\hyperv
  .\Run-HyperV-Smoke.ps1 -Action fresh
  .\Run-HyperV-Smoke.ps1 -Action smoke-fresh
  .\Run-HyperV-Smoke.ps1 -Action upgrade
  .\Run-HyperV-Smoke.ps1 -Action smoke-upgrade
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('fresh', 'smoke-fresh', 'upgrade', 'smoke-upgrade', 'destroy', 'status')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$logDir = Join-Path $env:LOCALAPPDATA 'CyberPanelHyperVSmoke\logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$log = Join-Path $logDir "run-hyperv-smoke-$Action.log"

function Log($m) {
    $ts = Get-Date -Format 'HH:mm:ss'
    "[$ts] $m" | Tee-Object -FilePath $log -Append
}

Log "Action=$Action"
& (Join-Path $PSScriptRoot 'up.ps1') $Action -Provider vagrant *>&1 | Tee-Object -FilePath $log -Append
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Log 'RUN_OK'
