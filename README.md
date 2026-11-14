# Entrega 4: observabilidad con Prometheus y Grafana

El laboratorio conserva `flask1` (S1), `flask2` (S2), `flask3` (S3), NGINX y la red `lab_red`. Agrega Prometheus y Grafana: seis contenedores en total. NGINX distribuye por round-robin hacia Flask:5000 y reintenta errores de conexión con otro upstream. Prometheus consulta directamente `flask1:5000/metrics`, `flask2:5000/metrics` y `flask3:5000/metrics` cada 5 segundos. No hay puertos Flask publicados.

Archivos modificados: `Servidor/app.py`, `Servidor/requirements.txt`, `Servidor/Dockerfile` y `Servidor/compose.yaml`. Archivos nuevos: `Servidor/metrics.py`, `Servidor/prometheus.yml`, `Servidor/grafana/provisioning/datasources/prometheus.yml`, `Servidor/.env.example`, `.gitignore`, este README y los seis scripts de experimentación más `scripts/comun.py`. Se conserva `nginx.conf.txt` sin cambiar su contenido; Compose ahora monta ese nombre real. Los archivos de Cliente y la documentación histórica se conservan.

## Despliegue en Ubuntu, VM servidor

Requisitos: Docker Engine con Docker Compose v2, Python 3 y acceso a las imágenes Docker. Desde la raíz del proyecto:

```bash
cd Servidor
cp .env.example .env
nano .env  # asignar GRAFANA_ADMIN_PASSWORD; no subir .env al repositorio
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --tail=30
cd ..
python3 scripts/validar_entorno.py
```

Esperar unos 15 segundos al primer arranque y repetir la validación si los targets todavía no aparecen. Los scripts solo requieren la biblioteca estándar; Flask y prometheus_client se instalan dentro de la imagen.

Acceso local: aplicación <http://localhost:8080>, Prometheus <http://localhost:9090> (Status → Target health) y Grafana <http://localhost:3000> (usuario `admin`, contraseña de `.env`). Grafana provisiona exclusivamente la fuente `Prometheus`, URL interna `http://prometheus:9090`, intervalo 5s. En Connections → Data sources → Prometheus comprobar **Save & test**. También se puede verificar autenticado con `curl -u admin http://127.0.0.1:3000/api/datasources/uid/prometheus` (solicita la contraseña).

Los volúmenes `prometheus_data` y `grafana_data` conservan métricas y dashboards guardados manualmente. Para parar: `cd Servidor && docker compose down`; no usar `down -v`. La contraseña de `.env` inicializa Grafana solo al crear su almacenamiento por primera vez; cambiarla después requiere la administración de Grafana.

## Endpoints e instrumentación

`/` devuelve JSON con el identificador por defecto; el navegador recibe la página HTML original al solicitar `text/html`. Se conservan calculadora, pruebas, monitor y APIs. `/health` devuelve JSON de estado. `/work?ms=50` espera entre 0 y 10000 ms; `/error?code=500` devuelve errores intencionales entre 400 y 599. Parámetros inválidos responden 400. `/metrics` expone Prometheus.

`http_requests_total` tiene etiquetas `node`, `method`, `endpoint` (plantilla de ruta o `unmatched`) y `status`. Métodos desconocidos se agrupan en `OTHER`. `http_requests_inprogress` y `http_request_duration_seconds` tienen etiqueta `node`. Las consultas de `/metrics` no cuentan como tráfico. Los hooks de cierre registran también errores y liberan la concurrencia. Cada contenedor ejecuta un único proceso Flask con hilos, como en la Entrega 3.

```bash
curl -s http://127.0.0.1:8080/
curl -s http://127.0.0.1:8080/health
curl -s 'http://127.0.0.1:8080/work?ms=50'
curl -i 'http://127.0.0.1:8080/error?code=500'
curl -s http://127.0.0.1:8080/metrics
```

El último comando muestra una réplica elegida por NGINX; Prometheus recolecta las tres directamente. La latencia interna del histograma comprende procesamiento Flask, sin red ni espera del cliente; el CSV mide extremo a extremo, incluida lectura de respuesta. No son medidas equivalentes. `up=0` significa que Prometheus no pudo recolectar esa instancia, mientras que una respuesta 200 de `/health` por NGINX indica disponibilidad global. Los errores de conexión/502 de NGINX no aparecen en contadores Flask si nunca llegan a Flask; se observan en los CSV y logs de NGINX.

## Dashboards construidos manualmente

No se incluyen dashboards JSON ni imports. En Grafana: Dashboards → New → New dashboard → Add visualization → Prometheus. Elegir modo **Code**, pegar una consulta de la tabla, seleccionar visualización y unidad, aplicar y guardar el dashboard. Usar rango de últimos 15 minutos, actualización de 5s y una ventana que incluya el experimento. Las consultas `rate` necesitan al menos dos scrapes y pueden no mostrar series antes de generar tráfico; ausencia de una serie de errores todavía no creada no significa fallo del datasource. En paneles por nodo usar leyenda `{{node}}`; para `up`, `{{instance}}`.

Dashboard **Rendimiento** (7 paneles; mínimo requerido 4):

| Panel | PromQL | Visualización / unidad |
|---|---|---|
| RPS global | `sum(rate(http_requests_total[1m]))` | Time series / req/s |
| RPS por instancia | `sum by (node) (rate(http_requests_total[1m]))` | Time series / req/s |
| Latencia promedio | `1000 * sum(rate(http_request_duration_seconds_sum[1m])) / sum(rate(http_request_duration_seconds_count[1m]))` | Time series / ms |
| Latencia P95 | `1000 * histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[2m])))` | Time series / ms |
| Errores 4xx | `sum(rate(http_requests_total{status=~"4.."}[1m]))` | Time series / req/s |
| Errores 5xx | `sum(rate(http_requests_total{status=~"5.."}[1m]))` | Time series / req/s |
| Concurrencia | `sum by (node) (http_requests_inprogress)` | Time series / solicitudes |

Dashboard **Disponibilidad y fallos** (5 paneles):

| Panel | PromQL | Visualización / ajustes |
|---|---|---|
| Estado por instancia | `up{job="flask_app"}` | Stat, consulta Instant; mapear 0=DOWN rojo, 1=UP verde |
| Instancias disponibles | `sum(up{job="flask_app"})` | Stat / rango 0–3, Instant |
| Distribución por nodo | `sum by (node) (increase(http_requests_total[$__range]))` | Pie chart / Instant, número de solicitudes estimado |
| Errores durante fallos | `sum by (status) (rate(http_requests_total{status=~"[45].."}[1m]))` | Time series, leyenda `{{status}}` |
| Caída y recuperación | `up{job="flask_app"}` | State timeline; 0=DOWN, 1=UP, leyenda `{{instance}}` |

`increase` es una estimación con extrapolación; el reparto exacto del experimento procede del CSV. Los contadores reinician al reiniciar un proceso y `rate` contempla esos reinicios. Una ventana de 1–2 minutos suaviza una caída breve; correlacionar con `resultados/eventos.csv`. La concurrencia se muestrea cada 5s y puede perder picos breves.

## Diez experimentos (desde la raíz)

Los CSV se crean con ejecuciones reales en `resultados/`; elegir un nombre nuevo si ya existe. La tasa limita los inicios globales; no garantiza alcanzar esa tasa si los hilos o el servidor se saturan. Throughput = intentos completados / tiempo entre primer inicio y último fin; P95 usa rango más próximo. El resumen incluye latencias de todos los intentos, también fallidos. No mezclar CSV de eventos con los de solicitudes.

1. Infraestructura y seis contenedores:
   ```bash
   docker compose -f Servidor/compose.yaml ps
   docker compose -f Servidor/compose.yaml exec nginx nginx -t
   docker compose -f Servidor/compose.yaml exec prometheus promtool check config /etc/prometheus/prometheus.yml
   ```
2. Tres targets UP (también verificar `up{job="flask_app"}` en Prometheus):
   ```bash
   python3 scripts/validar_entorno.py
   ```
3. Balanceo secuencial de 90 solicitudes:
   ```bash
   python3 scripts/generador_carga.py --requests 90 --concurrency 1 --path / --output resultados/normal.csv
   ```
4. Latencias de trabajo, 100 solicitudes y 10 hilos por escenario:
   ```bash
   python3 scripts/generador_carga.py --requests 100 --concurrency 10 --path '/work?ms=50' --output resultados/work50.csv
   python3 scripts/generador_carga.py --requests 100 --concurrency 10 --path '/work?ms=200' --output resultados/work200.csv
   ```
5. Carga progresiva, cada escenario dura aproximadamente un minuto:
   ```bash
   python3 scripts/generador_carga.py --requests 240 --concurrency 10 --rate 4 --path '/work?ms=50' --output resultados/rps4.csv
   python3 scripts/generador_carga.py --requests 480 --concurrency 10 --rate 8 --path '/work?ms=50' --output resultados/rps8.csv
   python3 scripts/generador_carga.py --requests 720 --concurrency 10 --rate 12 --path '/work?ms=50' --output resultados/rps12.csv
   ```
6. Comparación de concurrencia en la misma ruta:
   ```bash
   python3 scripts/generador_carga.py --requests 100 --concurrency 1 --path '/work?ms=50' --output resultados/hilos1.csv
   python3 scripts/generador_carga.py --requests 100 --concurrency 20 --path '/work?ms=50' --output resultados/hilos20.csv
   ```
7. Veinte errores 500, cinco hilos:
   ```bash
   python3 scripts/generador_carga.py --requests 20 --concurrency 5 --path '/error?code=500' --output resultados/error500.csv
   ```
8. Fallo: en terminal A iniciar monitor; en terminal B esperar 10 segundos, detener flask1 y generar solicitudes:
   ```bash
   # Terminal A
   python3 scripts/monitor_disponibilidad.py --duration 90 --interval 1 --output resultados/disponibilidad.csv
   # Terminal B
   sleep 10
   python3 scripts/pruebas_fallos.py stop flask1
   sleep 10
   python3 scripts/generador_carga.py --requests 90 --concurrency 1 --path / --output resultados/fallo.csv
   ```
   Comprobar `up{job="flask_app"}`: flask1=0 y las otras dos=1. NGINX debe continuar atendiendo. El monitor es evidencia independiente del servicio global.
9. Recuperación, mientras terminal A sigue monitoreando:
   ```bash
   python3 scripts/pruebas_fallos.py start flask1
   sleep 15
   python3 scripts/validar_entorno.py
   python3 scripts/generador_carga.py --requests 90 --concurrency 1 --path / --output resultados/recuperacion.csv
   ```
   Confirmar tres targets UP y retorno de S1 al CSV. Si se interrumpe el ensayo, ejecutar igualmente `start flask1`. No usar `down` para simular fallo de una sola instancia.
10. Comparación cuantitativa por archivo:
    ```bash
    python3 scripts/analizar_resultados.py resultados/normal.csv resultados/rps12.csv resultados/fallo.csv resultados/recuperacion.csv resultados/disponibilidad.csv
    python3 scripts/analizar_resultados.py resultados/work50.csv resultados/work200.csv resultados/hilos1.csv resultados/hilos20.csv resultados/error500.csv
    ```
    Registrar total, éxitos, errores HTTP, errores de conexión, reparto S1/S2/S3, promedio, P95 y throughput. Los cuatro escenarios usan cargas distintas: describir esta diferencia al interpretar sus cifras. Para comparar aisladamente el efecto del fallo, repetir con idéntica ruta, hilos, cantidad y tasa antes/durante/después. Conservar horas y capturas de ambos dashboards. No hay resultados experimentales precargados.

## VM cliente mediante SSH

En el cliente, definir un alias SSH `vm-servidor` en `~/.ssh/config` con el usuario y nombre DNS/mDNS o dirección actual de la VM servidor. Si cambia su dirección, actualizar solo ese alias; no hay IP fija en scripts ni Compose. El servidor debe permitir SSH. Con los puertos locales libres en el cliente:

```bash
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:8080:127.0.0.1:8080 -L 127.0.0.1:9090:127.0.0.1:9090 -L 127.0.0.1:3000:127.0.0.1:3000 vm-servidor
```

Mantener abierta esa terminal; abrir las mismas URLs localhost en el cliente. Copiar `scripts/` al cliente permite ejecutar carga, monitor y análisis contra el túnel. `pruebas_fallos.py` debe ejecutarse en la VM servidor donde están Compose y Docker. El cliente histórico puede usarse con `python3 Cliente/cliente_pruebas.py --url http://127.0.0.1:8080 -n 30`; sus instrucciones antiguas de acceso directo ya no corresponden a esta entrega. Solo SSH necesita acceso entre VM; 8080, 9090 y 3000 permanecen vinculados a loopback.

## Validación

```bash
python3 -m compileall -q Servidor scripts Cliente
cd Servidor
docker compose config --quiet
docker compose up -d --build
```

Validaciones realizadas en el entorno de implementación: `docker compose config --quiet` correcto, seis servicios declarados, Python sin errores de sintaxis, endpoints existentes y nuevos probados con el cliente Flask, respuestas JSON/HTML, exclusión de `/metrics`, agrupación de rutas desconocidas, errores 500 y excepciones propagadas sin dejar concurrencia pendiente. Se verificaron tres solicitudes simultáneas y retorno del gauge a cero. También se ejecutaron generador, monitor y análisis contra Flask local con CSV temporales reales: límite de 10 RPS, registro de errores 500 y rechazo de rutas externas. Se comprobó por separado el registro de errores de conexión. Esas comprobaciones locales no representan los resultados de los diez experimentos.

Luego ejecutar las verificaciones y endpoints anteriores, comprobar la fuente Grafana, detener y recuperar flask1 y repetir la validación. No eliminar volúmenes ni resultados. En el entorno de implementación el cliente Docker está instalado, pero el motor no responde: las comprobaciones de contenedores, scraping real, datasource en ejecución y fallo/recuperación quedan pendientes hasta disponer del motor Docker. Las pruebas locales Flask no sustituyen esas verificaciones.

Referencias: [cliente Python de Prometheus](https://prometheus.github.io/client_python/) y [provisioning de Grafana](https://grafana.com/docs/grafana/latest/administration/provisioning/).
