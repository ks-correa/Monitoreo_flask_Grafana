"""Pruebas HTTP desde la VM cliente sin escribir IPs en el código.
Uso: python3 cliente_pruebas.py -n 30
Configurar SERVER_IP en el archivo cliente.env.
"""
import argparse
import collections
import json
from pathlib import Path
import time
import urllib.request


def leer_configuracion():
    ruta = Path(__file__).with_name('cliente.env')
    if not ruta.exists():
        raise SystemExit('Falta cliente.env: copia cliente.env.ejemplo y cambia SERVER_IP.')
    opciones = {}
    for linea in ruta.read_text(encoding='utf-8').splitlines():
        linea = linea.strip()
        if linea and not linea.startswith('#') and '=' in linea:
            clave, valor = linea.split('=', 1)
            opciones[clave.strip()] = valor.strip()
    if not opciones.get('SERVER_IP'):
        raise SystemExit('Define SERVER_IP en cliente.env.')
    return f"http://{opciones['SERVER_IP']}:{opciones.get('SERVER_PORT', '8080')}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', help='URL opcional para pruebas puntuales')
    parser.add_argument('-n', type=int, default=30)
    args = parser.parse_args()
    if args.n < 1:
        parser.error('El número de solicitudes debe ser positivo')
    base = args.url or leer_configuracion()
    counts = collections.Counter()
    times = []
    errors = []
    for i in range(args.n):
        start = time.perf_counter()
        try:
            url = base.rstrip('/') + '/api/estado?i=' + str(i)
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.load(response)
            counts[data['servidor']] += 1
            times.append((time.perf_counter() - start) * 1000)
        except Exception as exc:
            errors.append(str(exc))
    print('URL:', base)
    print('Solicitudes:', args.n)
    print('Respuestas por servidor:', dict(counts))
    print('Errores:', len(errors))
    if times:
        print('Latencia media (ms):', round(sum(times) / len(times), 2))
        print('Latencia máxima (ms):', round(max(times), 2))
    if errors:
        print('Ejemplos de errores:', errors[:3])


if __name__ == '__main__':
    main()
