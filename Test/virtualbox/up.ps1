param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('fresh', 'upgrade', 'smoke-fresh', 'smoke-upgrade', 'halt', 'destroy', 'status')]
    [string]$Action,

    [Parameter()]
    [ValidateSet('9', '10')]
    [string]$Os = '9'
)

$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

if ($Os -eq '10') {
    # VirtualBox on Windows Hypervisor masks AVX2, so the default
    # almalinux/10 (x86-64-v3) dies at /init. Official v2 box still runs EL10.
    $env:CYBERPANEL_BOX = 'almalinux/10-x86_64_v2'
} else {
    $env:CYBERPANEL_BOX = 'almalinux/9'
}

function Assert-Tools {
    foreach ($name in @('vagrant', 'VBoxManage')) {
        if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
            throw "Missing $name. Install VirtualBox 7.x and Vagrant, then reopen the terminal."
        }
    }
}

function Invoke-Vagrant {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$VagrantArgs)
    & vagrant @VagrantArgs
    if ($LASTEXITCODE -ne 0) {
        throw "vagrant $($VagrantArgs -join ' ') failed with exit code $LASTEXITCODE"
    }
}

Assert-Tools
Write-Host "Box: $($env:CYBERPANEL_BOX)"

switch ($Action) {
    'fresh' {
        Write-Host "Starting cp-fresh on $($env:CYBERPANEL_BOX) (master3395 v3.0.2-dev). This takes 15-40 minutes."
        Invoke-Vagrant up cp-fresh --provider virtualbox
    }
    'upgrade' {
        Write-Host "Starting cp-upgrade on $($env:CYBERPANEL_BOX) (stock v3.0.2 then v3.0.2-dev). This takes 30-60 minutes."
        Invoke-Vagrant up cp-upgrade --provider virtualbox
    }
    'smoke-fresh' {
        Invoke-Vagrant ssh cp-fresh -c "tr -d '\r' < /vagrant/smoke.sh | sudo bash"
        Write-Host 'Panel URL: https://127.0.0.1:18090  password: TestPass12'
    }
    'smoke-upgrade' {
        Invoke-Vagrant ssh cp-upgrade -c "tr -d '\r' < /vagrant/smoke.sh | sudo bash"
        Write-Host 'Panel URL: https://127.0.0.1:28090  password: TestPass12'
    }
    'halt' {
        vagrant halt cp-fresh
        vagrant halt cp-upgrade
    }
    'destroy' {
        vagrant destroy -f cp-fresh
        vagrant destroy -f cp-upgrade
    }
    'status' {
        Invoke-Vagrant status
    }
}
