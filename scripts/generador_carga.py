"""Carga al balanceador local con límite global de inicios por segundo."""
import argparse
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit

from comun import ROOT, consultar, destino_libre, guardar, resumir


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--requests', type=int, default=90)
    parser.add_argument('--concurrency', type=int, default=1)
    parser.add_argument('--rate', type=float)
    parser.add_argument('--path', default='/')
    parser.add_argument('--output', default=str(ROOT / 'resultados/carga.csv'))
    args = parser.parse_args()
    if args.requests < 1 or args.concurrency < 1 or (args.rate is not None and not 0 < args.rate < float('inf')):
        parser.error('requests, concurrency y rate deben ser positivos y finitos')
    parts = urlsplit(args.path)
    if not args.path.startswith('/') or args.path.startswith('//') or parts.scheme or parts.netloc or parts.fragment or '\\' in args.path:
        parser.error('path debe ser una ruta local, por ejemplo /work?ms=50')
    destino_libre(parser, args.output)
    gate = threading.Lock()
    next_start = 0.0

    def send(number):
        nonlocal next_start
        if args.rate:
            with gate:
                delay = next_start - time.perf_counter()
                if delay > 0:
                    time.sleep(delay)
                next_start = time.perf_counter() + 1 / args.rate
        return consultar('http://127.0.0.1:8080' + args.path, number)

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        rows = list(pool.map(send, range(1, args.requests + 1)))
    guardar(rows, args.output)
    resumir(rows)


if __name__ == '__main__':
    main()
