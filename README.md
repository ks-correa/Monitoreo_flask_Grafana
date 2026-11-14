# Entrega 4: observabilidad con Prometheus y Grafana

El laboratorio conserva `flask1` (S1), `flask2` (S2), `flask3` (S3), NGINX y la red `lab_red`. Agrega Prometheus y Grafana: seis contenedores en total. NGINX distribuye por round-robin hacia Flask:5000 y reintenta errores de conexión con otro upstream. Prometheus consulta directamente `flask1:5000/metrics`, `flask2:5000/metrics` y `flask3:5000/metrics` cada 5 segundos. No hay puertos Flask publicados.

NGINX usa el DNS interno de Docker (`127.0.0.11`), una zona compartida y `resolve` para actualizar las IP de Flask sin reiniciar el balanceador. Conserva round-robin. El DNS se renueva cada 5s; detectar un fallo y retornar al nodo recuperado puede requerir unos segundos. El tiempo de conexión a una réplica se limita a 1s para reintentar pronto en otra cuando una IP detenida no responde; no limita la duración del trabajo en `/work`.

## Inicio desde Windows (PowerShell)

Requisitos: Docker Desktop iniciado con contenedores Linux y Python 3.10+ para los scripts. Desde la raíz:

```powershell
# Solo si todavía no existe Servidor/.env:
Copy-Item Servidor/.env.example Servidor/.env
notepad Servidor/.env
# Definir GRAFANA_ADMIN_PASSWORD, guardar y cerrar el editor.
.\Servidor\iniciar_windows.ps1
python scripts/validar_entorno.py
```

No sobrescribir `.env` existente. En Linux usar `python3` si corresponde. En PowerShell sustituir `sleep 10`/`sleep 15` por `Start-Sleep -Seconds 10`/`Start-Sleep -Seconds 15`.

## Inicio en Linux/macOS

Requisitos: Docker con Compose v2, Python 3.10+ y acceso a las imágenes Docker. Desde la raíz del proyecto:

```bash
cd Servidor
# Solo si todavía no existe .env:
cp -n .env.example .env
nano .env  # asignar GRAFANA_ADMIN_PASSWORD; no subir .env al repositorio
bash iniciar_linux.sh
docker compose logs --tail=30
cd ..
python scripts/validar_entorno.py
```

Esperar unos 15 segundos al primer arranque y repetir la validación si los targets todavía no aparecen. Los scripts solo requieren la biblioteca estándar; Flask y prometheus_client se instalan dentro de la imagen.

Acceso local: aplicación <http://localhost:8080>, Prometheus <http://localhost:9090> (Status → Target health) y Grafana <http://localhost:3000> (usuario `admin`, contraseña de `.env`). Grafana provisiona exclusivamente la fuente `Prometheus`, URL interna `http://prometheus:9090`, intervalo 5s. En Connections → Data sources → Prometheus comprobar **Save & test**.

Los volúmenes `prometheus_data` y `grafana_data` conservan métricas y dashboards guardados manualmente. Para parar: `cd Servidor && docker compose down`; no usar `down -v`. La contraseña de `.env` inicializa Grafana solo al crear su almacenamiento por primera vez; cambiarla después requiere la administración de Grafana.

## Endpoints e instrumentación

`/` siempre devuelve JSON con `nodo`, incluso desde el navegador. Se conservan calculadora, pruebas, monitor y APIs. `/health` devuelve JSON de estado. `/work?ms=50` espera entre 0 y 10000 ms; `/error?code=500` devuelve errores intencionales entre 400 y 599. Parámetros inválidos responden 400. `/metrics` expone Prometheus.

`http_requests_total` tiene etiquetas `node`, `method`, `endpoint` (plantilla de ruta o `unmatched`) y `status`. Métodos desconocidos se agrupan en `OTHER`. `http_requests_inprogress` y `http_request_duration_seconds` tienen etiqueta `node`. Las consultas de `/metrics` no cuentan como tráfico. Los hooks de cierre registran también errores y liberan la concurrencia. Cada contenedor ejecuta un único proceso Flask con hilos, como en la Entrega 3.

```bash
curl -s http://127.0.0.1:8080/
curl -s http://127.0.0.1:8080/health
curl -s 'http://127.0.0.1:8080/work?ms=50'
curl -i 'http://127.0.0.1:8080/error?code=500'
curl -s http://127.0.0.1:8080/metrics
```

El último comando muestra una réplica elegida por NGINX; Prometheus recolecta las tres directamente. La latencia interna del histograma comprende procesamiento Flask, sin red ni espera del cliente; el CSV mide extremo a extremo, incluida lectura de respuesta. No son medidas equivalentes. `up=0` significa que Prometheus no pudo recolectar esa instancia, mientras que una respuesta 200 de `/health` por NGINX indica disponibilidad global. Los errores de conexión/502 de NGINX no aparecen en contadores Flask si nunca llegan a Flask; se observan en los CSV y logs de NGINX.

## Dos dashboards manuales

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

## Diez experimentos (desde la raíz)

Los CSV se crean con ejecuciones reales en `resultados/`; elegir un nombre nuevo si ya existe. La tasa limita los inicios globales; no garantiza alcanzar esa tasa si los hilos o el servidor se saturan. Throughput = intentos completados / tiempo entre primer inicio y último fin; P95 usa rango más próximo. El resumen incluye latencias de todos los intentos, también fallidos. Los CSV incluyen `exitosa` (1 o 0); los antiguos sin esa columna siguen siendo analizables: se calculan los éxitos usando HTTP y errores de conexión. `disponibilidad_observada_pct` = 100 × éxitos / intentos; para el monitor de `/health` representa disponibilidad global observada de NGINX, no disponibilidad temporal continua ni porcentaje de targets UP. Para el ensayo `/error`, representa solo la proporción de respuestas exitosas de ese ensayo. No mezclar CSV de eventos con los de solicitudes.

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
    Registrar total, éxitos, errores HTTP, errores de conexión, reparto S1/S2/S3, promedio, P95, throughput y porcentaje de disponibilidad observado en el monitor. Los cuatro escenarios usan cargas distintas: describir esta diferencia al interpretar sus cifras. Conservar horas y capturas de ambos dashboards. Los resultados anteriores se conservan en `resultados/historicos/`, separados de las pruebas oficiales nuevas en `resultados/`.
