import argparse
import csv
import subprocess
from datetime import datetime

from comun import ROOT


def main():
    parser = argparse.ArgumentParser(description='Detiene o inicia una instancia del laboratorio')
    parser.add_argument('accion', choices=['stop', 'start'])
    parser.add_argument('servicio', choices=['flask1', 'flask2', 'flask3'])
    args = parser.parse_args()
    inicio = datetime.now().astimezone().isoformat(timespec='milliseconds')
    result = subprocess.run(['docker', 'compose', args.accion, args.servicio], cwd=ROOT / 'Servidor')
    path = ROOT / 'resultados/eventos.csv'
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists() or path.stat().st_size == 0
    with path.open('a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if new:
            writer.writerow(['inicio', 'fin', 'accion', 'servicio', 'codigo_salida'])
        writer.writerow([inicio, datetime.now().astimezone().isoformat(timespec='milliseconds'), args.accion, args.servicio, result.returncode])
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
