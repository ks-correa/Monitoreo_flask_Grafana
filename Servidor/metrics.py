"""Métricas por proceso: cada contenedor ejecuta una instancia Flask."""
from time import perf_counter

from flask import Response, g, request
from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, CONTENT_TYPE_LATEST, generate_latest, disable_created_metrics

# Exponer solo las tres métricas del laboratorio.
disable_created_metrics()
REGISTRY = CollectorRegistry()

REQUESTS = Counter('http_requests_total', 'Solicitudes HTTP', ['node', 'method', 'endpoint', 'status'], registry=REGISTRY)
INPROGRESS = Gauge('http_requests_inprogress', 'Solicitudes en curso', ['node'], registry=REGISTRY)
DURATION = Histogram('http_request_duration_seconds', 'Duración interna de Flask', ['node'], registry=REGISTRY)


def instrumentar(app, node):
    concurrency = INPROGRESS.labels(node)
    duration = DURATION.labels(node)

    @app.before_request
    def comenzar():
        if request.path != '/metrics':
            g.metric_start = perf_counter()
            g.metric_status = 500
            concurrency.inc()

    @app.after_request
    def estado(response):
        if hasattr(g, 'metric_start'):
            g.metric_status = response.status_code
        return response

    @app.teardown_request
    def terminar(error):
        start = g.pop('metric_start', None)
        if start is None:
            return
        try:
            endpoint = request.url_rule.rule if request.url_rule else 'unmatched'
            method = request.method if request.method in {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'} else 'OTHER'
            REQUESTS.labels(node, method, endpoint, str(g.metric_status)).inc()
            duration.observe(perf_counter() - start)
        finally:
            concurrency.dec()

    @app.get('/metrics')
    def metrics():
        return Response(generate_latest(REGISTRY), content_type=CONTENT_TYPE_LATEST)
