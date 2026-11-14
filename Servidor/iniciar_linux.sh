#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -f .env ]]; then
    echo 'Falta .env. Copia .env.example a .env y define GRAFANA_ADMIN_PASSWORD.' >&2
    exit 1
fi
if ! command -v docker >/dev/null 2>&1; then
    echo 'No se encuentra Docker. Se requiere Docker Engine con Compose v2.' >&2
    exit 1
fi
if ! docker compose config --quiet; then
    echo 'Revisa .env: debes definir GRAFANA_ADMIN_PASSWORD y una configuración Compose válida.' >&2
    exit 1
fi
docker compose up -d --build
docker compose ps
