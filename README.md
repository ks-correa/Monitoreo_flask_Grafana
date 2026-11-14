# Entrega 4: observabilidad con Prometheus y Grafana

El laboratorio conserva `flask1` (S1), `flask2` (S2), `flask3` (S3), NGINX y la red `lab_red`. Agrega Prometheus y Grafana: seis contenedores en total. NGINX distribuye por round-robin hacia Flask:5000 y reintenta errores de conexión con otro upstream. Prometheus consulta directamente `flask1:5000/metrics`, `flask2:5000/metrics` y `flask3:5000/metrics` cada 5 segundos. No hay puertos Flask publicados.

NGINX usa el DNS interno de Docker (`127.0.0.11`), una zona compartida y `resolve` para actualizar las IP de Flask sin reiniciar el balanceador. Conserva round-robin. El DNS se renueva cada 5s; detectar un fallo y retornar al nodo recuperado puede requerir unos segundos. El tiempo de conexión a una réplica se limita a 1s para reintentar pronto en otra cuando una IP detenida no responde; no limita la duración del trabajo en `/work`.

## Inicio desde Windows (PowerShell)

Requisitos: Docker Desktop iniciado con contenedores Linux y Python 3 para los scripts. Desde la raíz:

```powershell
# Solo si todavía no existe Servidor/.env:
Copy-Item Servidor/.env.example Servidor/.env
notepad Servidor/.env
# Definir GRAFANA_ADMIN_PASSWORD, guardar y cerrar el editor.
.\Servidor\iniciar_windows.ps1
python scripts/validar_entorno.py
```

No sobrescribir un `.env` existente. Si la política de PowerShell bloquea el script, usar estos comandos sin cambiar la configuración del sistema:

```powershell
cd Servidor
docker compose config --quiet
docker compose up -d --build
docker compose ps
cd ..
```

Los scripts de inicio comprueban `.env` y una contraseña no vacía; no crean ni muestran contraseñas. Para los experimentos siguientes, en Windows sustituir `python3` por `python` y `sleep 10`/`sleep 15` por `Start-Sleep -Seconds 10`/`Start-Sleep -Seconds 15`. Las rutas con `/` y argumentos entre comillas funcionan también en PowerShell.

## Despliegue en Ubuntu, VM servidor

Requisitos: Docker Engine con Docker Compose v2, Python 3 y acceso a las imágenes Docker. Desde la raíz del proyecto:

```bash
cd Servidor
# Solo si todavía no existe .env:
cp -n .env.example .env
nano .env  # asignar GRAFANA_ADMIN_PASSWORD; no subir .env al repositorio
bash iniciar_linux.sh
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

Seguir [GUIA_GRAFANA.md](GUIA_GRAFANA.md): consultas PromQL exactas, visualizaciones, unidades, leyendas, configuración e interpretación de cinco paneles de **Rendimiento** y cuatro de **Disponibilidad y fallos**. Construir ambos manualmente en Grafana, con actualización de 5s y rango de 15 minutos. No se generan ni importan dashboards JSON. La distribución de carga durante el fallo se observa como RPS por nodo en una serie temporal.

## Diez experimentos (desde la raíz)

Los CSV se crean con ejecuciones reales en `resultados/`; elegir un nombre nuevo si ya existe. La tasa limita los inicios globales; no garantiza alcanzar esa tasa si los hilos o el servidor se saturan. Throughput = intentos completados / tiempo entre primer inicio y último fin; P95 usa rango más próximo. El resumen incluye latencias de todos los intentos, también fallidos. Los CSV incluyen `exitosa` (1 o 0); los antiguos sin esa columna siguen siendo analizables: se calculan los éxitos usando HTTP y errores de conexión. `disponibilidad_observada_pct` = 100 × éxitos / intentos; para el monitor de `/health` representa disponibilidad global observada de NGINX, no disponibilidad temporal continua ni porcentaje de targets UP. Para el ensayo `/error`, representa solo la proporción de respuestas exitosas de ese ensayo. No mezclar CSV de eventos con los de solicitudes.

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
   Para observar 30 respuestas por nodo en este CSV, cerrar monitores y páginas que consulten las APIs durante esta prueba. Las solicitudes concurrentes de otros clientes también participan en el round-robin.
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
    Registrar total, éxitos, errores HTTP, errores de conexión, reparto S1/S2/S3, promedio, P95, throughput y porcentaje de disponibilidad observado en el monitor. Los cuatro escenarios usan cargas distintas: describir esta diferencia al interpretar sus cifras. Para comparar aisladamente el efecto del fallo, repetir con idéntica ruta, hilos, cantidad y tasa antes/durante/después. Conservar horas y capturas de ambos dashboards. No hay resultados experimentales precargados.

## VM cliente mediante SSH

En el cliente, definir un alias SSH `vm-servidor` en `~/.ssh/config` con el usuario y nombre DNS/mDNS o dirección actual de la VM servidor. Si cambia su dirección, actualizar solo ese alias; no hay IP fija en scripts ni Compose. El servidor debe permitir SSH. Con los puertos locales libres en el cliente:

```bash
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:8080:127.0.0.1:8080 -L 127.0.0.1:9090:127.0.0.1:9090 -L 127.0.0.1:3000:127.0.0.1:3000 vm-servidor
```

Mantener abierta esa terminal; abrir las mismas URLs localhost en el cliente. Copiar `scripts/` al cliente permite ejecutar carga, monitor y análisis contra el túnel. `pruebas_fallos.py` debe ejecutarse en la VM servidor donde están Compose y Docker. El cliente histórico puede usarse con `python3 Cliente/cliente_pruebas.py --url http://127.0.0.1:8080 -n 30`; sus instrucciones antiguas de acceso directo ya no corresponden a esta entrega. Solo SSH necesita acceso entre VM; 8080, 9090 y 3000 permanecen vinculados a loopback.

## Evidencias para la entrega

Conservar `docker compose ps` con seis contenedores activos, la validación de NGINX y Prometheus, los tres targets UP, flask1 DOWN con flask2/flask3 UP y el retorno de flask1 a UP. Capturar ambos dashboards con rango y leyendas visibles durante carga, errores y fallo/recuperación. Adjuntar CSV originales, `resultados/eventos.csv` y resúmenes; relacionar horas de eventos con la línea temporal. El CSV del monitor debe cubrir antes, durante y después del fallo. No rellenar resultados supuestos.

## Validación

```bash
python3 -m compileall -q Servidor scripts Cliente
cd Servidor
docker compose config --quiet
bash iniciar_linux.sh
```

Archivos nuevos de finalización: `GUIA_GRAFANA.md`, `Servidor/iniciar_windows.ps1`, `Servidor/iniciar_linux.sh` y `.gitattributes` (finales LF para Bash). Correcciones: `Servidor/nginx.conf.txt` (DNS dinámico y tiempo de conexión), `scripts/comun.py` (éxito explícito, disponibilidad observada y errores de protocolo), `Cliente/cliente.env.ejemplo` (localhost) y esta documentación. Se conservan aplicación, APIs, seis servicios y red existente.

Validaciones reales realizadas desde Windows con Docker Desktop el 13 de noviembre de 2026:

- Sintaxis Python, YAML, PowerShell y Bash; Compose válido; `nginx -t` y `promtool check config` correctos.
- Endpoints, interfaz HTML, calculadora, métricas, exclusión de `/metrics`, concurrencia y cierre correcto ante excepciones comprobados localmente.
- Seis contenedores levantados, tres targets UP y datasource de Grafana comprobado mediante su API, incluida la conexión a Prometheus. Las once consultas PromQL de la guía se ejecutaron correctamente.
- Scripts de CSV, análisis compatible con CSV anteriores, tasa de inicios, errores HTTP y de conexión y rechazo de rutas externas verificados. Ambos scripts de inicio rechazan `.env` ausente o contraseña vacía; el inicio PowerShell se ejecutó con éxito.
- En `resultados/validacion_20261113_204335/`: 90 solicitudes repartidas 30/30/30, veinte errores HTTP 500 registrados y una carga corta de ocho solicitudes a 4 RPS. Este primer ensayo de fallo detectó tiempos de conexión excesivos y motivó el ajuste de NGINX; sus CSV se conservaron.
- En `resultados/validacion_20261113_204543/`: 30/30 solicitudes correctas con flask1 detenido; 30/30 correctas tras recuperarlo; monitor con 129/129 muestras correctas, disponibilidad global observada de 100%. Se observó flask1 DOWN y luego UP.
- Al cambiar realmente la IP de flask1, NGINX volvió a enviarle tráfico sin reiniciarse. `cambio_ip.csv` conserva un 502 transitorio durante la actualización y 29/30 respuestas correctas; `ip_estabilizada.csv` confirma después 90/90 correctas, con reparto 30/30/30. La recuperación DNS automática no garantiza ausencia absoluta de errores durante una modificación de red. Este cambio de IP es una comprobación adicional, distinta del experimento normal `stop`/`start`.

Se conservan también los CSV de ejecuciones de validación interrumpidas y todos los eventos reales en `resultados/eventos.csv`. Estos ensayos de desarrollo no sustituyen las diez pruebas académicas completas. Al terminar quedaron seis contenedores activos y flask1 restaurado.

Pendiente en las VM Ubuntu: ejecutar el inicio Bash con Docker Engine real, comprobar el túnel SSH entre ambas VM, repetir las diez pruebas con sus parámetros originales, construir los dashboards manualmente y recopilar las capturas y CSV oficiales. No se requieren cambios de software para comenzar ese despliegue.

Referencias: [cliente Python de Prometheus](https://prometheus.github.io/client_python/), [provisioning de Grafana](https://grafana.com/docs/grafana/latest/administration/provisioning/) y [resolución dinámica de NGINX](https://nginx.org/en/docs/http/ngx_http_upstream_module.html#resolve).
