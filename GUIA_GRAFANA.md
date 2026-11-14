# Construcción manual de los dashboards

Abrir <http://localhost:3000>, entrar como `admin` con la contraseña configurada y comprobar en **Connections → Data sources → Prometheus** que la URL sea `http://prometheus:9090`. No importar JSON ni dashboards del catálogo.

Para cada dashboard: **Dashboards → New → New dashboard → Add visualization → Prometheus**. En **Queries**, seleccionar **Code**, pegar la consulta y pulsar **Run queries**. Usar consultas **Range** para series y **Instant** solo donde se indique. Elegir visualización en el selector de la derecha, título en **Panel options**, unidad en **Standard options → Unit** y leyenda personalizada en **Options → Legend** de cada consulta. Aplicar o volver al dashboard y guardarlo con **Save dashboard**. Los nombres de controles pueden variar con el idioma de Grafana.

En ambos dashboards seleccionar **Last 15 minutes** y actualización **5s** (arriba a la derecha). Guardar el rango y la actualización al guardar el dashboard. Prometheus recolecta cada 5s; generar tráfico antes de interpretar las series y esperar dos scrapes como mínimo. Para las curvas de un minuto, mantener tráfico alrededor de un minuto facilita la lectura.

## Dashboard 1: Rendimiento (cinco paneles)

### 1. Solicitudes por segundo globales

```promql
sum(rate(http_requests_total[1m]))
```

- Visualización: **Time series**; unidad personalizada `req/s`; leyenda `Global`.
- Configuración: consulta Range, mínimo del eje Y en 0, leyenda visible.
- Significado: tasa agregada de solicitudes procesadas por las tres instancias, incluidos `/health` y errores; excluye `/metrics`.

### 2. Solicitudes por segundo por instancia

```promql
sum by (node) (rate(http_requests_total[1m]))
```

- Visualización: **Time series**; unidad `req/s`; leyenda `{{node}}`.
- Configuración: Range, mínimo 0, sin apilar para comparar S1, S2 y S3 por separado.
- Significado: reparto de solicitudes entre instancias. Con round-robin y solicitudes equivalentes, las curvas deben aproximarse.

### 3. Latencia promedio y P95

Consulta A, leyenda `Promedio`:

```promql
1000 * sum(rate(http_request_duration_seconds_sum[1m])) / sum(rate(http_request_duration_seconds_count[1m]))
```

Consulta B (**Add query**), leyenda `P95`:

```promql
1000 * histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[2m])))
```

- Visualización: **Time series**; unidad **Time → milliseconds (ms)**.
- Configuración: ambas Range, mínimo 0, sin apilar; misma escala para ambas.
- Significado: promedio y estimación del percentil 95 del tiempo interno de Flask. El P95 se estima con los buckets del histograma y puede exceder la espera exacta de `/work`. Sus ventanas son diferentes (1m y 2m). El CSV mide latencia extremo a extremo; comparar indicando esta diferencia. Sin solicitudes nuevas puede aparecer NaN o ausencia de datos.

### 4. Errores HTTP 4xx y 5xx

Consulta A, leyenda `4xx`:

```promql
sum(rate(http_requests_total{status=~"4.."}[1m]))
```

Consulta B, leyenda `5xx`:

```promql
sum(rate(http_requests_total{status=~"5.."}[1m]))
```

- Visualización: **Time series**; unidad `req/s`.
- Configuración: ambas Range, mínimo 0, leyenda visible, sin apilar.
- Significado: frecuencia de respuestas de error producidas por Flask. Una serie de errores aún no creada puede no aparecer; generar el error correspondiente antes de comprobarla. No incluye errores generados únicamente por NGINX ni conexiones fallidas del cliente.

### 5. Solicitudes simultáneas

```promql
sum by (node) (http_requests_inprogress)
```

- Visualización: **Time series**; unidad **Misc → Short**, etiqueta del eje `solicitudes`; leyenda `{{node}}`.
- Configuración: Range, mínimo 0, decimales 0, sin apilar.
- Significado: solicitudes en procesamiento por nodo en cada scrape. Un 0 no descarta trabajo entre scrapes; esperas breves pueden pasar inadvertidas con muestreo de 5s.

Guardar como **Rendimiento**.

## Dashboard 2: Disponibilidad y fallos (cuatro paneles)

### 1. Estado UP/DOWN de las tres instancias

```promql
up{job="flask_app"}
```

- Visualización: **Stat**; unidad **Misc → Short**; leyenda `{{instance}}`.
- Configuración: **Instant**, **Show → All values**, decimales 0. En **Value mappings** agregar `0 → DOWN` rojo y `1 → UP` verde; **Color mode → Background**. Deben aparecer tres valores, uno por instancia. Mantener ausencia de datos diferenciada de DOWN.
- Significado: éxito de la última recolección de cada instancia por Prometheus. UP no es una medición de disponibilidad global de NGINX ni valida todos los endpoints.

### 2. Distribución de carga durante un fallo

```promql
sum by (node) (rate(http_requests_total[1m]))
```

- Visualización: **Time series**; unidad `req/s`; leyenda `{{node}}`.
- Configuración: Range, mínimo 0, sin apilar, leyenda con colores distintos para cada nodo. Mantener **Connect null values → Never**.
- Significado: permite ver cómo el RPS deja de recibirse en S1 y pasa a S2 y S3 durante su caída; luego S1 vuelve a recibir solicitudes. La ventana de 1m suaviza las transiciones y la serie de S1 puede desaparecer mientras está detenida. Por eso no se utiliza un gráfico circular acumulado para este panel. Mantener tráfico antes, durante y después para observar el reparto; correlacionar las horas con `resultados/eventos.csv`.

### 3. Errores durante el experimento

```promql
sum by (status) (rate(http_requests_total{status=~"[45].."}[1m]))
```

- Visualización: **Time series**; unidad `req/s`; leyenda `HTTP {{status}}`.
- Configuración: Range, mínimo 0, sin apilar. Seleccionar el rango que incluye las pruebas de error y fallo.
- Significado: errores HTTP registrados por Flask, desglosados por código. Un fallo de instancia no necesariamente provoca errores al usuario porque NGINX puede reenviar la solicitud a otra. Los errores de NGINX y de conexión se verifican en los CSV; este panel no los cuenta.

### 4. Línea temporal de caída y recuperación

```promql
up{job="flask_app"}
```

- Visualización: **State timeline**; unidad **Misc → Short**; leyenda `{{instance}}`.
- Configuración: Range, mapear `0 → DOWN` rojo y `1 → UP` verde, **Merge equal consecutive values** activado, **Connect null values → Never**. No convertir valores ausentes en UP.
- Significado: muestra el período de caída y retorno de cada target. Las horas de detección pueden diferir hasta un intervalo de scrape respecto a los eventos reales; las marcas exactas del comando están en `eventos.csv`.

Guardar como **Disponibilidad y fallos**.

## Evidencia e interpretación

Tomar capturas de ambos dashboards con título, rango, ejes y leyendas visibles: tráfico normal, 4/8/12 RPS, comparación 50/200 ms y 1/20 hilos, errores 500 y período de fallo/recuperación. Capturar también los tres targets UP, S1 DOWN con las otras dos UP y su retorno a UP. Mantener el reloj de ambas VM sincronizado.

Para disponibilidad global usar el CSV de `monitor_disponibilidad.py` y su análisis: `disponibilidad_observada_pct = 100 × solicitudes exitosas / total de intentos`. Una solicitud exitosa tiene HTTP 200–399 y no presenta error de conexión; `/health` normalmente devuelve 200. Es un porcentaje de muestras observadas, no una garantía de disponibilidad continua ni el porcentaje de targets UP. Separar el ensayo intencional de errores 500 del monitor de `/health`.

La distribución exacta y las latencias del cliente se obtienen de CSV reales. No completar tablas con valores supuestos. Conservar los dashboards guardados en el volumen de Grafana, sin generar ni importar dashboards JSON.
