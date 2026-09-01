param(
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$PanelDir = $PSScriptRoot
$MatrixPath = Join-Path $PanelDir 'os-matrix.json'
$Matrix = Get-Content $MatrixPath -Raw | ConvertFrom-Json

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'docker is required'
}

Write-Host "Refreshing base digests in $MatrixPath ..."

foreach ($entry in $Matrix) {
    $base = $entry.base
    Write-Host "  $($entry.tag): pulling $base ..."
    try {
        docker pull $base | Out-Null
        $inspect = docker inspect --format='{{index .RepoDigests 0}}' $base 2>$null
        if ($inspect -and $inspect -match '@(.+)$') {
            $entry.digest = $Matches[1]
        } else {
            $entry.digest = (docker image inspect $base --format='{{.Id}}' 2>$null)
        }
    } catch {
        Write-Warning "Pull failed for $($entry.tag); keeping empty digest"
        $entry.digest = ''
    }
}

if ($DryRun) {
    $Matrix | ConvertTo-Json -Depth 5
} else {
    $Matrix | ConvertTo-Json -Depth 5 | Set-Content -Path $MatrixPath -Encoding UTF8
    Write-Host "Done. Review $MatrixPath and commit digest updates when ready."
}
