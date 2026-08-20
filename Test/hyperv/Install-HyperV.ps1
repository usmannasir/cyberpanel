#Requires -RunAsAdministrator
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
Import-Module (Join-Path $PSScriptRoot 'HyperV-Smoke.psm1') -Force
Install-HyperVSmokeFeature
Write-Host ''
Write-Host 'If Windows prompted for a reboot, reboot now before running .\up.ps1 fresh'
