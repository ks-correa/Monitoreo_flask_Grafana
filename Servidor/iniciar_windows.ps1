$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    if (-not (Test-Path -LiteralPath '.env' -PathType Leaf)) {
        throw 'Falta .env. Copia .env.example a .env y define GRAFANA_ADMIN_PASSWORD.'
    }
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'No se encuentra Docker. Inicia Docker Desktop antes de continuar.'
    }
    # Compose comprueba también que la contraseña no esté vacía, sin mostrarla.
    docker compose config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Revisa .env: debes definir GRAFANA_ADMIN_PASSWORD y una configuración Compose válida.' }
    docker compose up -d --build
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo levantar el proyecto. Comprueba que el motor Docker esté iniciado.' }
    docker compose ps
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo consultar el estado de los contenedores.' }
}
finally {
    Pop-Location
}
