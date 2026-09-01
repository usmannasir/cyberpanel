param(
    [string]$Os = 'all',
    [switch]$NoCache
)

$ErrorActionPreference = 'Stop'
$PanelDir = $PSScriptRoot
$RepoRoot = Resolve-Path (Join-Path $PanelDir '..\..')
$MatrixPath = Join-Path $PanelDir 'os-matrix.json'
$Matrix = Get-Content $MatrixPath -Raw | ConvertFrom-Json
$Revision = ''
try {
    $Revision = (git -C $RepoRoot rev-parse HEAD 2>$null)
} catch {
    $Revision = 'local'
}

if ($Os -ne 'all') {
    $Matrix = @($Matrix | Where-Object { $_.tag -eq $Os })
    if (-not $Matrix) { throw "Unknown OS tag: $Os" }
}

foreach ($entry in $Matrix) {
    $baseImage = $entry.base
    if ($entry.digest -and $entry.digest -ne '') {
        $baseImage = "$($entry.base)@$($entry.digest)"
    }
    $tag = "master3395/cyberpanel:$($entry.tag)"
    Write-Host "Building $tag from $baseImage ..."
    $args = @(
        'build',
        '-f', (Join-Path $PanelDir 'Dockerfile'),
        '--build-arg', "BASE_IMAGE=$baseImage",
        '--build-arg', "OS_FAMILY=$($entry.family)",
        '--build-arg', "OS_TAG=$($entry.tag)",
        '--build-arg', "IMAGE_REVISION=$Revision",
        '-t', $tag
    )
    if ($entry.tag -eq 'almalinux10') {
        $args += '-t', 'master3395/cyberpanel:latest'
    }
    if ($NoCache) { $args += '--no-cache' }
    $args += $RepoRoot
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "Build failed for $($entry.tag)" }
}

Write-Host 'Build matrix complete.'
