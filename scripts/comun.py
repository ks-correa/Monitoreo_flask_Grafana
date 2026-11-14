"""HTTP local, CSV y resumen compartidos por los experimentos."""
import csv
import json
import math
import statistics
import time
from collections import Counter
from datetime import datetime
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ['fecha_hora', 'solicitud', 'nodo', 'status', 'latencia_ms', 'error_conexion', 'inicio_epoch', 'fin_epoch', 'exitosa']


class SinRedireccion(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def consultar(url, numero):
    inicio = time.time()
    reloj = time.perf_counter()
    row = dict(fecha_hora=datetime.now().astimezone().isoformat(timespec='milliseconds'),
               solicitud=numero, nodo='', status=0, error_conexion='', inicio_epoch=inicio)
    # Sin proxies ni redirecciones: las pruebas permanecen en localhost.
    opener = build_opener(ProxyHandler({}), SinRedireccion())
    try:
        try:
            response = opener.open(url, timeout=10)
        except HTTPError as exc:
            response = exc
        with response:
            row['status'] = response.code
            row['nodo'] = response.headers.get('X-Servidor-Flask', '')
            body = response.read()
            try:
                data = json.loads(body)
                if isinstance(data, dict):
                    row['nodo'] = data.get('nodo', row['nodo'])
            except (ValueError, UnicodeError):
                pass
    except (URLError, OSError, TimeoutError, HTTPException) as exc:
        row['error_conexion'] = str(exc)
    row['latencia_ms'] = round((time.perf_counter() - reloj) * 1000, 3)
    row['fin_epoch'] = time.time()
    row['exitosa'] = int(200 <= row['status'] < 400 and not row['error_conexion'])
    return row


def guardar(rows, output):
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Evita sobrescribir evidencia de una ejecución anterior.
    with path.open('x', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print('CSV:', path)


def resumir(rows):
    if not rows:
        print('Sin solicitudes.')
        return
    latencies = sorted(float(r['latencia_ms']) for r in rows)
    successes = sum(200 <= int(r['status']) < 400 and not r['error_conexion'] for r in rows)
    http_errors = sum(int(r['status']) >= 400 for r in rows)
    connections = sum(bool(r['error_conexion']) for r in rows)
    elapsed = max(float(r['fin_epoch']) for r in rows) - min(float(r['inicio_epoch']) for r in rows)
    print(json.dumps(dict(total=len(rows), exitosas=successes, errores_http=http_errors,
                          disponibilidad_observada_pct=round(100 * successes / len(rows), 3),
                          errores_conexion=connections, errores=len(rows)-successes,
                          distribucion=dict(Counter(r['nodo'] for r in rows if r['nodo'])),
                          latencia_promedio_ms=round(statistics.mean(latencies), 3),
                          p95_ms=latencies[math.ceil(.95 * len(latencies))-1],
                          duracion_s=round(elapsed, 3),
                          throughput_rps=round(len(rows)/elapsed, 3) if elapsed > 0 else 0),
                     ensure_ascii=False, indent=2))


def destino_libre(parser, output):
    if Path(output).exists():
        parser.error(f'El archivo ya existe: {output}; elige otro --output')
