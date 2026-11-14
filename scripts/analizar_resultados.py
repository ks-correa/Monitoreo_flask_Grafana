import argparse
import csv

from comun import resumir


def main():
    parser = argparse.ArgumentParser(description='Resumen por escenario; no mezcla periodos separados')
    parser.add_argument('archivos', nargs='+')
    args = parser.parse_args()
    for path in args.archivos:
        print('\nEscenario:', path)
        with open(path, newline='', encoding='utf-8') as file:
            resumir(list(csv.DictReader(file)))


if __name__ == '__main__':
    main()
