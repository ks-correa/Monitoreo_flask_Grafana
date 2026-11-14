# Laboratorio de observabilidad de la Entrega 4

Seguir [la guía original del profesor](Guia_Estudiante_Entrega4.docx). Este repositorio contiene el código y las configuraciones de partida; `resultados/` comienza vacío para registrar únicamente las pruebas que realices.

## Fase 1. Preparar y verificar la topología

Requisitos: Docker con Compose v2 (en Windows, Docker Desktop con contenedores Linux), Python 3.10+, navegador y puertos locales 8080, 9090 y 3000 disponibles. Internet se necesita inicialmente para descargar imágenes y paquetes. Los scripts Python usan la biblioteca estándar; la imagen instala las dependencias de `Servidor/requirements.txt`.

La topología contiene `flask1`, `flask2`, `flask3`, `nginx`, `prometheus` y `grafana` en la red `lab_red`. NGINX distribuye round-robin a Flask:5000; solo NGINX, Prometheus y Grafana publican puertos en localhost.

Desde la raíz, copiar `.env.example` únicamente si todavía no existe `.env`, editar la contraseña `GRAFANA_ADMIN_PASSWORD` y ejecutar el inicio.

Windows (PowerShell):

```powershell
Copy-Item Servidor/.env.example Servidor/.env
notepad Servidor/.env
.\Servidor\iniciar_windows.ps1
```

Linux/macOS:

```bash
cp -n Servidor/.env.example Servidor/.env
# Editar Servidor/.env y definir GRAFANA_ADMIN_PASSWORD
bash Servidor/iniciar_linux.sh
```

No subir `.env` ni contraseñas. En los comandos siguientes usar `python3` si corresponde en Linux.

```bash
docker compose -f Servidor/compose.yaml ps
python scripts/validar_entorno.py
```

Abrir [NGINX](http://localhost:8080), [Prometheus](http://localhost:9090/targets) y [Grafana](http://localhost:3000). En Grafana usar `admin` y la contraseña de `.env`. Esperar unos 15 segundos para las primeras recolecciones antes de repetir la validación.

Para detener el proyecto conservando los datos:

```bash
docker compose -f Servidor/compose.yaml stop
```

Los volúmenes `lab-nginx_prometheus_data` y `lab-nginx_grafana_data` conservan métricas y dashboards entre arranques. Si ya contienen datos, el inicio no los reinicia: acordar su borrado antes de comenzar si se necesita un almacenamiento vacío.

## Fase 2. Revisar la instrumentación y comprobar Flask

Inspeccionar `Servidor/app.py` y `Servidor/metrics.py`. La instrumentación ya está preparada: identificar y explicar Counter `http_requests_total` (node, method, endpoint, status), Gauge `http_requests_inprogress` y Histogram `http_request_duration_seconds` (node). `/metrics` no suma tráfico. Las rutas desconocidas se agrupan en `unmatched` y los métodos desconocidos en `OTHER`.

Comprobar las rutas desde localhost:

```bash
curl -s http://localhost:8080/
curl -s http://localhost:8080/health
curl -s "http://localhost:8080/work?ms=50"
curl -i "http://localhost:8080/error?code=500"
docker compose -f Servidor/compose.yaml exec flask1 python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:5000/metrics').read().decode()[:500])"
```

En PowerShell usar `curl.exe` si `curl` es un alias. `/` debe responder JSON con `nodo`, incluso en navegador. Se conservan `/calculadora`, `/pruebas`, `/monitor`, `/api/estado` y `/api/calcular` de la Entrega 3.

## Fase 3. Recolectar métricas con Prometheus

Revisar `Servidor/prometheus.yml`: job `flask_app`, intervalo de 5 segundos y targets `flask1:5000`, `flask2:5000`, `flask3:5000`, ruta `/metrics`. Comprobar los tres targets en <http://localhost:9090/targets>.

Para observar tráfico sostenido usar el escenario de 480 solicitudes a 8 RPS de la prueba 5. Tras varias recolecciones, consultar en Prometheus e interpretar las unidades:

```promql
up{job="flask_app"}
sum by (node) (rate(http_requests_total[1m]))
1000 * histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[2m])))
```

Si se ejecuta ese escenario aquí, conservar su CSV para la prueba 5 o elegir otro nombre al repetirlo.

## Fase 4. Construir los dashboards manualmente

Usar la fuente aprovisionada **Prometheus** (`http://prometheus:9090`). Crear ambos dashboards desde cero, exactamente cuatro paneles cada uno, sin importar JSON. Seleccionar Prometheus y modo Code; agregar las consultas de cada fila al mismo panel. Guardar con rango de 15 minutos y refresco de 5 segundos.

### Rendimiento

| Panel | PromQL | Visualización y unidad |
|---|---|---|
| RPS global y por servidor | `sum(rate(http_requests_total[1m]))` y `sum by (node) (rate(http_requests_total[1m]))` | Time series, req/s; leyendas Global y `{{node}}` |
| Latencia promedio y P95 | `1000 * sum(rate(http_request_duration_seconds_sum[1m])) / sum(rate(http_request_duration_seconds_count[1m]))` y `1000 * histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[2m])))` | Time series, ms; leyendas Promedio y P95 |
| Errores HTTP 4xx y 5xx | `sum(rate(http_requests_total{status=~"4.."}[1m]))` y `sum(rate(http_requests_total{status=~"5.."}[1m]))` | Time series, req/s; leyendas 4xx y 5xx |
| Solicitudes simultáneas | `sum by (node) (http_requests_inprogress)` | Time series, solicitudes, 0 decimales; leyenda `{{node}}` |

### Disponibilidad y fallos

| Panel | PromQL | Visualización y unidad |
|---|---|---|
| Estado de las tres instancias | `up{job="flask_app"}` | Stat, Instant, All values; leyenda `{{instance}}` |
| Distribución de carga después de un fallo | `sum by (node) (rate(http_requests_total[1m]))` | Time series, req/s; leyenda `{{node}}` |
| Errores durante el experimento | `sum by (status) (rate(http_requests_total{status=~"[45].."}[1m]))` | Time series, req/s; leyenda `HTTP {{status}}` |
| Línea temporal de recuperación | `up{job="flask_app"}` | State timeline; leyenda `{{instance}}` |

Usar consultas Range salvo el Stat, mínimo 0 y sin apilar. En Stat y State timeline mapear 0 a DOWN rojo y 1 a UP verde. No conectar valores ausentes ni convertirlos en UP. Esperar al menos dos scrapes con tráfico antes de interpretar tasas. Un panel vacío no demuestra caída. El muestreo de 5 segundos puede omitir picos breves de concurrencia. Correlacionar la línea temporal con eventos.csv y la disponibilidad global con el CSV del monitor.

## Fase 5. Ejecutar las diez pruebas e interpretar resultados

Ejecutar desde la raíz. Usar nombres nuevos si los CSV ya existen. Por cada prueba formular una hipótesis, ejecutar el procedimiento, conservar CSV y capturas propias y escribir la interpretación y conclusión. El archivo de eventos se genera al detener/iniciar instancias; no pasarlo al analizador de solicitudes.

1. Infraestructura y seis contenedores:
   ```bash
   docker compose -f Servidor/compose.yaml ps
   python scripts/validar_entorno.py
   ```
2. Scraping: verificar tres targets UP en <http://localhost:9090/targets> y consultar `up{job="flask_app"}` en Prometheus.
3. Balanceo secuencial de 90 solicitudes:
   ```bash
   python scripts/generador_carga.py --requests 90 --concurrency 1 --path / --output resultados/normal.csv
   ```
   Para observar 30 respuestas por nodo en este CSV, cerrar monitores y páginas que consulten las APIs durante esta prueba. Las solicitudes concurrentes de otros clientes también participan en el round-robin.
4. Latencias de trabajo, 100 solicitudes y 10 hilos por escenario:
   ```bash
   python scripts/generador_carga.py --requests 100 --concurrency 10 --path '/work?ms=50' --output resultados/latencia50.csv
   python scripts/generador_carga.py --requests 100 --concurrency 10 --path '/work?ms=200' --output resultados/latencia200.csv
   ```
5. Carga progresiva, cada escenario dura aproximadamente un minuto:
   ```bash
   python scripts/generador_carga.py --requests 240 --concurrency 10 --rate 4 --path '/work?ms=50' --output resultados/rps4.csv
   python scripts/generador_carga.py --requests 480 --concurrency 10 --rate 8 --path '/work?ms=50' --output resultados/rps8.csv
   python scripts/generador_carga.py --requests 720 --concurrency 10 --rate 12 --path '/work?ms=50' --output resultados/rps12.csv
   ```
6. Comparación de concurrencia en la misma ruta:
   ```bash
   python scripts/generador_carga.py --requests 100 --concurrency 1 --path '/work?ms=50' --output resultados/hilos1.csv
   python scripts/generador_carga.py --requests 100 --concurrency 20 --path '/work?ms=50' --output resultados/hilos20.csv
   ```
7. Veinte errores 500, cinco hilos:
   ```bash
   python scripts/generador_carga.py --requests 20 --concurrency 5 --path '/error?code=500' --output resultados/errores.csv
   ```
8. Fallo: en terminal A iniciar monitor; en terminal B esperar 10 segundos, detener flask1 y generar solicitudes:
   ```bash
   # Terminal A
   python scripts/monitor_disponibilidad.py --duration 90 --interval 1 --output resultados/disponibilidad.csv
   # Terminal B
   sleep 10
   python scripts/pruebas_fallos.py stop flask1
   sleep 10
   python scripts/generador_carga.py --requests 90 --concurrency 1 --path / --output resultados/fallo.csv
   ```
   Comprobar `up{job="flask_app"}`: flask1=0 y las otras dos=1. NGINX debe continuar atendiendo. El monitor es evidencia independiente del servicio global.
9. Recuperación, mientras terminal A sigue monitoreando:
   ```bash
   python scripts/pruebas_fallos.py start flask1
   sleep 15
   python scripts/validar_entorno.py
   python scripts/generador_carga.py --requests 90 --concurrency 1 --path / --output resultados/recuperacion.csv
   ```
   Confirmar tres targets UP y retorno de S1 al CSV. Si se interrumpe el ensayo, ejecutar igualmente `start flask1`. No usar `down` para simular fallo de una sola instancia.
10. Comparación cuantitativa por archivo:
    ```bash
    python scripts/analizar_resultados.py resultados/normal.csv resultados/rps12.csv resultados/fallo.csv resultados/recuperacion.csv resultados/disponibilidad.csv
    python scripts/analizar_resultados.py resultados/latencia50.csv resultados/latencia200.csv resultados/hilos1.csv resultados/hilos20.csv resultados/errores.csv
    ```
    Registrar total, éxitos, errores HTTP, errores de conexión, reparto S1/S2/S3, promedio, P95, throughput y porcentaje de disponibilidad observado en el monitor. Los cuatro escenarios usan cargas distintas: describir esta diferencia al interpretar sus cifras. Conservar horas y capturas de ambos dashboards.
