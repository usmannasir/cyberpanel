param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('fresh', 'upgrade', 'smoke-fresh', 'smoke-upgrade', 'halt', 'destroy', 'status')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

function Assert-Tools {
    foreach ($name in @('vagrant', 'VBoxManage')) {
        if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
            throw "Missing $name. Install VirtualBox 7.x and Vagrant, then reopen the terminal."
        }
    }
}

Assert-Tools

switch ($Action) {
    'fresh' {
        Write-Host 'Starting cp-fresh (silent install of master3395 v3.0.2-dev). This takes 15-40 minutes.'
        vagrant up cp-fresh --provider virtualbox
    }
    'upgrade' {
        Write-Host 'Starting cp-upgrade (stock v3.0.2 then upgrade to v3.0.2-dev). This takes 30-60 minutes.'
        vagrant up cp-upgrade --provider virtualbox
    }
    'smoke-fresh' {
        vagrant ssh cp-fresh -c "tr -d '\r' < /vagrant/smoke.sh | sudo bash"
        Write-Host 'Panel URL: https://127.0.0.1:18090  password: TestPass12'
    }
    'smoke-upgrade' {
        vagrant ssh cp-upgrade -c "tr -d '\r' < /vagrant/smoke.sh | sudo bash"
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
        vagrant status
    }
}
