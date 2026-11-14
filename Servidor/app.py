import os
import time

from flask import Flask, jsonify, request
from metrics import instrumentar

app = Flask(__name__)
nodo = os.getenv("SERVER_ID", "S1")
instrumentar(app, nodo)


@app.after_request
def identificar(respuesta):
    respuesta.headers["X-Servidor-Flask"] = nodo
    return respuesta


@app.get("/")
def inicio():
    return jsonify(nodo=nodo, estado="ok")


@app.get("/health")
def health():
    return jsonify(nodo=nodo, status="ok")


@app.get("/work")
def work():
    try:
        ms = int(request.args.get("ms", "50"))
        if not 0 <= ms <= 10000:
            raise ValueError
    except ValueError:
        return jsonify(nodo=nodo, error="ms inválido"), 400

    time.sleep(ms / 1000)
    return jsonify(nodo=nodo, ms=ms)


@app.get("/error")
def error():
    try:
        code = int(request.args.get("code", "500"))
        if not 400 <= code <= 599:
            raise ValueError
    except ValueError:
        return jsonify(nodo=nodo, error="Código HTTP inválido"), 400

    return jsonify(nodo=nodo, error="Error intencional"), code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), threaded=True)
