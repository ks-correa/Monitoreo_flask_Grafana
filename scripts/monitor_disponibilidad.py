import argparse
import math
import time

from comun import ROOT, consultar, destino_libre, guardar, resumir


def main():
    parser = argparse.ArgumentParser(description='Disponibilidad global de NGINX desde localhost')
    parser.add_argument('--duration', type=float, default=90)
    parser.add_argument('--interval', type=float, default=1)
    parser.add_argument('--output', default=str(ROOT / 'resultados/disponibilidad.csv'))
    args = parser.parse_args()
    if not all(math.isfinite(n) and n > 0 for n in [args.duration, args.interval]):
        parser.error('duration e interval deben ser positivos y finitos')
    destino_libre(parser, args.output)
    rows = []
    deadline = time.perf_counter() + args.duration
    try:
        while time.perf_counter() < deadline:
            start = time.perf_counter()
            rows.append(consultar('http://127.0.0.1:8080/health', len(rows)+1))
            time.sleep(max(0, min(args.interval - (time.perf_counter()-start), deadline-time.perf_counter())))
    except KeyboardInterrupt:
        pass
    guardar(rows, args.output)
    resumir(rows)


if __name__ == '__main__':
    main()
