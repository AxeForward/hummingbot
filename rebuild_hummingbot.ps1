param(
    [string]$ComposeFile = "docker-compose.yml",
    [string]$Service = "hummingbot",
    [string]$ContainerName = "hummingbot",
    [string]$ImageName = "hummingbot-paradex:latest",
    [switch]$NoAttach
)

$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [string]$Message,
        [scriptblock]$Action
    )
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
    & $Action
}

function Remove-Container-IfExists {
    param([string]$Name)
    $id = docker ps -aq --filter "name=^${Name}$"
    if ($id) {
        Write-Host "Removing container: $Name" -ForegroundColor Yellow
        docker rm -f $Name | Out-Null
    }
}

function Remove-Image-IfExists {
    param([string]$Name)
    $id = docker images -q $Name
    if ($id) {
        Write-Host "Removing image: $Name" -ForegroundColor Yellow
        docker image rm -f $Name | Out-Null
    }
}

if (-not (Test-Path $ComposeFile)) {
    throw "Compose file not found: $ComposeFile"
}

Invoke-Step "docker compose down (remove orphans)" {
    docker compose -f $ComposeFile down --remove-orphans
}

Invoke-Step "force remove leftover container(s)" {
    Remove-Container-IfExists -Name $ContainerName
}

Invoke-Step "remove old local image" {
    Remove-Image-IfExists -Name $ImageName
}

Invoke-Step "build image locally (no pull, no cache)" {
    docker compose -f $ComposeFile build --no-cache --pull=false $Service
}

Invoke-Step "start service in background" {
    docker compose -f $ComposeFile up -d $Service
}

if (-not $NoAttach) {
    Write-Host ""
    Write-Host "==> attaching to $ContainerName (detach with Ctrl+P, Ctrl+Q)" -ForegroundColor Cyan
    docker attach $ContainerName
}
