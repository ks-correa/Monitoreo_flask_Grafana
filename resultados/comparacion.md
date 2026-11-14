# Comparación cuantitativa de la Entrega 4

Ejecución real en localhost el 14 de noviembre de 2026. Las horas de los CSV incluyen su zona horaria.

| Escenario | Intentos | Errores | Promedio ms | P95 ms | Throughput RPS |
|---|---:|---:|---:|---:|---:|
| normal | 90 | 0 | 9.064 | 25.356 | 109.933 |
| latencia50 | 100 | 0 | 57.945 | 65.132 | 168.597 |
| latencia200 | 100 | 0 | 208.274 | 212.473 | 47.821 |
| rps4 | 240 | 0 | 56.816 | 71.688 | 4.008 |
| rps8 | 480 | 0 | 56.968 | 70.622 | 7.989 |
| rps12 | 720 | 0 | 56.492 | 69.301 | 11.959 |
| hilos1 | 100 | 0 | 57.925 | 73.345 | 17.253 |
| hilos20 | 100 | 0 | 58.727 | 68.519 | 307.552 |
| errores | 20 | 20 | 5.551 | 9.875 | 744.027 |
| fallo | 90 | 0 | 7.541 | 23.784 | 132.006 |
| recuperacion | 90 | 0 | 9.006 | 24.583 | 110.673 |
| disponibilidad | 90 | 0 | 21.288 | 26.202 | 1.011 |

El balanceo normal dio 30/30/30 respuestas. La espera de 200 ms aumentó promedio y P95 frente a 50 ms. Con 20 hilos aumentó el throughput frente a 1 hilo, con latencias individuales similares. Las tasas observadas de la carga progresiva se aproximaron a 4, 8 y 12 RPS. Los 20 errores fueron HTTP 500 intencionales, sin fallos de conexión.

Durante la caída, flask1 pasó a DOWN y S2/S3 atendieron las 90 solicitudes correctamente. Después, los tres targets volvieron a UP y S1 atendió 29 de las 90 solicitudes de recuperación. El monitor paralelo introduce tráfico adicional, por lo que el reparto de esos CSV no tiene que ser exacto. Los 90 sondeos de salud resultaron exitosos: disponibilidad global observada del 100%.

Normal, fallo y recuperación usan 90 solicitudes secuenciales a /. La carga progresiva usa /work?ms=50 con 10 hilos; su throughput no permite atribuir por sí solo diferencias al fallo. El throughput del monitor refleja el intervalo de sondeo, no capacidad máxima. La disponibilidad observada es una proporción de muestras; no garantiza disponibilidad continua.

Los estados reales están en targets_caida.json y targets_recuperacion.json; eventos.csv registra stop/start. analisis.txt contiene los resúmenes del analizador. Pendiente por el grupo: construir los dos dashboards manualmente, tomar capturas y completar hipótesis e interpretación del informe. No se generaron dashboards ni capturas ficticias.
