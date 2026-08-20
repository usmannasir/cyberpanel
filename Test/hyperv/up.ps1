param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('fresh', 'upgrade', 'smoke-fresh', 'smoke-upgrade', 'halt', 'destroy', 'status', 'bootstrap')]
    [string]$Action,

    [Parameter()]
    [ValidateSet('fresh', 'upgrade', 'all')]
    [string]$Profile = 'fresh',

    [Parameter()]
    [ValidateSet('native', 'vagrant')]
    [string]$Provider = 'native'
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
Import-Module (Join-Path $PSScriptRoot 'HyperV-Smoke.psm1') -Force

function Resolve-ProfileKey {
    param([string]$Name)
    if ($Name -eq 'all') { return 'fresh' }
    return $Name
}

switch ($Action) {
    'bootstrap' {
        if ($Provider -eq 'vagrant') {
            Write-Host 'Vagrant provider downloads almalinux/10 on first up.'
            return
        }
        Write-Host 'Caching AlmaLinux 10 VHDX template and tools (no VM created)...'
        $null = Get-AlmaTemplateVhdxPath
        Write-Host 'Bootstrap done.'
    }
    'fresh' {
        if ($Provider -eq 'vagrant') {
            vagrant up cp-fresh --provider=hyperv
            if ($LASTEXITCODE -ne 0) { throw "vagrant up cp-fresh failed with exit code $LASTEXITCODE" }
            Write-Host 'FRESH_INSTALL_DONE (vagrant)'
            return
        }
        $key = Resolve-ProfileKey $Profile
        if ($key -ne 'fresh') { throw 'Use -Profile fresh for fresh install.' }
        $vm = New-CpHyperVVm -Profile 'fresh'
        $ip = Get-CpVmIpv4 -VmName $vm -Profile 'fresh'
        Write-Host "Guest IP: $ip"
        Wait-CpVmSsh -Ip $ip
        $scriptPath = Join-Path $PSScriptRoot 'provision-fresh.sh'
        Invoke-CpGuestScript -Ip $ip -LocalScript $scriptPath
        Set-CpPanelPortProxy -Ip $ip -HostPort 18090
        Write-Host 'FRESH_INSTALL_DONE'
    }
    'upgrade' {
        if ($Provider -eq 'vagrant') {
            vagrant up cp-upgrade --provider=hyperv
            if ($LASTEXITCODE -ne 0) { throw "vagrant up cp-upgrade failed with exit code $LASTEXITCODE" }
            Write-Host 'UPGRADE_DONE (vagrant)'
            return
        }
        $vm = New-CpHyperVVm -Profile 'upgrade'
        $ip = Get-CpVmIpv4 -VmName $vm -Profile 'upgrade'
        Write-Host "Guest IP: $ip"
        Wait-CpVmSsh -Ip $ip
        $scriptPath = Join-Path $PSScriptRoot 'provision-upgrade.sh'
        Invoke-CpGuestScript -Ip $ip -LocalScript $scriptPath
        Set-CpPanelPortProxy -Ip $ip -HostPort 28090
        Write-Host 'UPGRADE_DONE'
    }
    'smoke-fresh' {
        if ($Provider -eq 'vagrant') {
            $env:VAGRANT_CWD = $PSScriptRoot
            $smoke = Join-Path $PSScriptRoot 'smoke.sh'
            Get-Content -Raw $smoke | vagrant ssh cp-fresh -c 'tr -d "\r" | bash'
            Write-Host 'Panel URL: https://127.0.0.1:18090  password: TestPass12'
            return
        }
        Import-HyperVSmokeModule
        $vm = 'cp-fresh-hv'
        if (-not (Get-VM -Name $vm -ErrorAction SilentlyContinue)) { throw "VM '$vm' missing. Run .\up.ps1 fresh first." }
        $ip = Get-CpVmIpv4 -VmName $vm -Profile 'fresh'
        Invoke-CpGuestSmoke -Ip $ip
        Set-CpPanelPortProxy -Ip $ip -HostPort 18090
    }
    'smoke-upgrade' {
        if ($Provider -eq 'vagrant') {
            $env:VAGRANT_CWD = $PSScriptRoot
            $smoke = Join-Path $PSScriptRoot 'smoke.sh'
            Get-Content -Raw $smoke | vagrant ssh cp-upgrade -c 'tr -d "\r" | bash'
            Write-Host 'Panel URL: https://127.0.0.1:28090  password: TestPass12'
            return
        }
        Import-HyperVSmokeModule
        $vm = 'cp-upgrade-hv'
        if (-not (Get-VM -Name $vm -ErrorAction SilentlyContinue)) { throw "VM '$vm' missing. Run .\up.ps1 upgrade first." }
        $ip = Get-CpVmIpv4 -VmName $vm -Profile 'upgrade'
        Invoke-CpGuestSmoke -Ip $ip
        Set-CpPanelPortProxy -Ip $ip -HostPort 28090
    }
    'halt' {
        if ($Profile -eq 'all') {
            Stop-CpHyperVVm -Profile 'fresh'
            Stop-CpHyperVVm -Profile 'upgrade'
        }
        else {
            Stop-CpHyperVVm -Profile (Resolve-ProfileKey $Profile)
        }
    }
    'destroy' {
        if ($Provider -eq 'vagrant') {
            vagrant destroy -f cp-fresh cp-upgrade 2>$null
            return
        }
        Remove-CpHyperVVm -Profile $Profile
    }
    'status' {
        Get-CpHyperVStatus
    }
}
