[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$docker = Get-Command docker -CommandType Application -ErrorAction SilentlyContinue
if (-not $docker) {
    Write-Output 'BLOCKED: Docker CLI is unavailable.'
    exit 2
}

& $docker.Source compose version
if ($LASTEXITCODE -ne 0) {
    Write-Output 'BLOCKED: Docker Compose v2 is unavailable.'
    exit 2
}

$engine = & $docker.Source info --format '{{.OSType}} {{.MemTotal}}'
if ($LASTEXITCODE -ne 0) {
    Write-Output 'BLOCKED: Docker Engine is unreachable.'
    exit 2
}

$platform, $bytes = $engine -split ' '
if ($platform -ne 'linux') {
    Write-Output 'BLOCKED: DIGIT CRS requires Docker to run Linux containers.'
    exit 2
}

$memoryGiB = [double]$bytes / 1GB
Write-Output ('Docker Engine memory: {0:N1} GiB.' -f $memoryGiB)
if ($memoryGiB -lt 8) {
    Write-Output 'The upstream local setup recommends allocating 8 GB to Docker.'
}
Write-Output 'READY: Linux Docker Engine and Compose v2 are reachable.'
