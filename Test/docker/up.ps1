param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('build', 'up', 'down', 'logs', 'smoke', 'smoke-full', 'smoke-minimal', 'status')]
    [string]$Action,

    [string]$Os = 'almalinux10',
    [ValidateSet('full', 'minimal', 'partial')]
    [string]$Mode = 'full',

    [string[]]$Enable = @()
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$PanelDir = Join-Path $RepoRoot 'docker\panel'
$Project = "cpdocker-$Os-$Mode"
$Image = "master3395/cyberpanel:$Os"

function Get-ComposeFile {
    if ($Mode -eq 'minimal') { return Join-Path $PanelDir 'docker-compose.minimal.yml' }
    return Join-Path $PanelDir 'docker-compose.yml'
}

function Get-ComposeEnv {
    $env:COMPOSE_PROJECT_NAME = $Project
    $env:CYBERPANEL_ADMIN_PASSWORD = if ($env:CYBERPANEL_ADMIN_PASSWORD) { $env:CYBERPANEL_ADMIN_PASSWORD } else { 'TestPass12' }
    $env:CYBERPANEL_BRANCH = if ($env:CYBERPANEL_BRANCH) { $env:CYBERPANEL_BRANCH } else { 'v3.0.4-dev' }
    $env:CYBERPANEL_REPO = if ($env:CYBERPANEL_REPO) { $env:CYBERPANEL_REPO } else { 'master3395' }
    if ($Mode -eq 'minimal') {
        $env:CYBERPANEL_MINIMAL = '1'
        $env:CYBERPANEL_FULL_INSTALL = '0'
    }
    elseif ($Mode -eq 'partial') {
        $env:CYBERPANEL_MINIMAL = '1'
        $env:CYBERPANEL_FULL_INSTALL = '0'
        $env:CYBERPANEL_ENABLE_POSTFIX = if ($Enable -contains 'postfix') { '1' } else { '0' }
        $env:CYBERPANEL_ENABLE_POWERDNS = if ($Enable -contains 'powerdns') { '1' } else { '0' }
        $env:CYBERPANEL_ENABLE_PUREFTPD = if ($Enable -contains 'pureftpd') { '1' } else { '0' }
    }
    else {
        $env:CYBERPANEL_MINIMAL = '0'
        $env:CYBERPANEL_FULL_INSTALL = '1'
    }
}

switch ($Action) {
    'build' {
        & (Join-Path $PanelDir 'build-matrix.ps1') -Os $Os
    }
    'up' {
        Get-ComposeEnv
        $compose = Get-ComposeFile
        docker compose -f $compose -p $Project up -d --build
        Write-Host "UP_OK project=$Project image=$Image mode=$Mode"
    }
    'down' {
        Get-ComposeEnv
        docker compose -f (Get-ComposeFile) -p $Project down -v
    }
    'logs' {
        docker logs -f cyberpanel 2>$null
        docker compose -f (Get-ComposeFile) -p $Project logs -f
    }
    'status' {
        docker compose -f (Get-ComposeFile) -p $Project ps
    }
    { $_ -in 'smoke', 'smoke-full', 'smoke-minimal' } {
        Get-ComposeEnv
        $script = switch ($Action) {
            'smoke-minimal' { 'smoke-minimal.sh' }
            'smoke-full' { 'smoke-full.sh' }
            default { 'smoke.sh' }
        }
        $local = Join-Path $PSScriptRoot $script
        docker compose -f (Get-ComposeFile) -p $Project exec -T cyberpanel bash -s < $local
    }
}
