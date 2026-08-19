param(
    [string]$Os = 'all',
    [switch]$NoCache
)

$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'build-matrix.ps1') -Os $Os -NoCache:$NoCache

$MatrixPath = Join-Path $PSScriptRoot 'os-matrix.json'
$Matrix = Get-Content $MatrixPath -Raw | ConvertFrom-Json
if ($Os -ne 'all') {
    $Matrix = @($Matrix | Where-Object { $_.tag -eq $Os })
}

foreach ($entry in $Matrix) {
    $tag = "master3395/cyberpanel:$($entry.tag)"
    Write-Host "Pushing $tag ..."
    docker push $tag
    if ($LASTEXITCODE -ne 0) { throw "Push failed for $tag" }
}

if ($Os -eq 'all' -or $Os -eq 'almalinux10') {
    docker push master3395/cyberpanel:latest
}

Write-Host 'Publish complete. Log in with: docker login -u master3395'
