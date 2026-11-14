# Entrega 4 — Observabilidad y monitoreo

Laboratorio de Flask, NGINX, Docker, Prometheus y Grafana. Seguir la [guía original del profesor](Guia_Estudiante_Entrega4.docx). La carpeta `resultados/` empieza vacía.

## Fase 1. Preparar y verificar la topología

Requisitos: Docker Compose v2, Python 3.10+ y navegador. En Windows, iniciar Docker Desktop.

Desde la raíz del repositorio:

```powershell
# Solo si .env no existe:
Copy-Item Servidor/.env.example Servidor/.env
notepad Servidor/.env
# Definir GRAFANA_ADMIN_PASSWORD y guardar.
.\Servidor\iniciar_windows.ps1
python scripts/validar_entorno.py
```

En Linux, copiar `Servidor/.env.example` a `Servidor/.env`, definir la contraseña y ejecutar `bash Servidor/iniciar_linux.sh`.

- NGINX: http://localhost:8080
- Prometheus: http://localhost:9090/targets
- Grafana: http://localhost:3000 (admin y contraseña de .env).

## Fases 2 a 5

| Fase | Actividad |
|---|---|
| 2 | Revisar app.py y metrics.py; comprobar los endpoints y las tres métricas. |
| 3 | Revisar prometheus.yml; comprobar los tres targets UP y las tres consultas PromQL de la guía. |
| 4 | Crear manualmente los dos dashboards de cuatro paneles cada uno. |
| 5 | Ejecutar las diez pruebas de la guía desde la raíz, guardar CSV, capturas y análisis. |

Los cinco scripts de la guía se encuentran en `scripts/`; `comun.py` contiene funciones compartidas. Todos operan sobre localhost. En Linux usar python3 si corresponde.

El directorio de infraestructura se llama `Servidor/`. Para ejecutar comandos Compose desde la raíz, usar `docker compose -f Servidor/compose.yaml`.

No compartir .env ni contraseñas. Para detener el laboratorio sin borrar métricas ni dashboards: `docker compose -f Servidor/compose.yaml down`.
