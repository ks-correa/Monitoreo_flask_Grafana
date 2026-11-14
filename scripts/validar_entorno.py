import json
from urllib.parse import urlencode
from urllib.request import ProxyHandler, build_opener


def main():
    opener = build_opener(ProxyHandler({}))
    failed = False

    def get(url):
        with opener.open(url, timeout=10) as response:
            return json.load(response)

    for name, url in [('NGINX', 'http://127.0.0.1:8080/health'),
                      ('Prometheus', 'http://127.0.0.1:9090/api/v1/status/buildinfo'),
                      ('Grafana', 'http://127.0.0.1:3000/api/health')]:
        try:
            data = get(url)
            if name == 'Grafana' and data.get('database') != 'ok':
                raise ValueError('Almacenamiento de Grafana no disponible')
            print(name, 'OK')
        except Exception as exc:
            print(name, 'ERROR:', exc)
            failed = True
    try:
        payload = get('http://127.0.0.1:9090/api/v1/targets')
        targets = [t for t in payload['data']['activeTargets'] if t['labels'].get('job') == 'flask_app']
        expected = {'flask1:5000', 'flask2:5000', 'flask3:5000'}
        if {t['labels']['instance'] for t in targets} != expected or len(targets) != 3:
            raise ValueError('Se esperaban exactamente los tres targets Flask')
        for target in targets:
            print(target['labels']['instance'], target['health'], target.get('lastError', ''))
            failed |= target['health'] != 'up'
        query = urlencode({'query': 'up{job="flask_app"}'})
        result = get('http://127.0.0.1:9090/api/v1/query?' + query)
        values = result['data']['result']
        if len(values) != 3 or any(float(v['value'][1]) != 1 for v in values):
            raise ValueError('La consulta up aún no devuelve las tres instancias UP')
    except Exception as exc:
        print('Targets ERROR:', exc)
        failed = True
    raise SystemExit(1 if failed else 0)


if __name__ == '__main__':
    main()
