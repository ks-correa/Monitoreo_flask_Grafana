# Entrega 3 - Fases 1 y 2

Este proyecto parte del laboratorio Nginx + Flask de la Entrega 2. Se conservan inicio, calculadora, generador de solicitudes, monitor, `/api/estado`, `/api/calcular` y `/health`.

## Adaptación (fase 1)
- Puerto interno predeterminado `5000` (`PORT` o `--port`).
- Escucha de Flask en `0.0.0.0`.
- Identificador desde `SERVER_ID` o `--id`.
- `/` muestra identificador, fecha/hora, estado y mensaje.
- `/health` responde HTTP 200 con JSON.

## Imagen (fase 2): VM servidor
```bash
cd ~/laboratorio_docker
docker build -t lab-flask:v1 .
docker image ls
docker run -d --rm --name flask-prueba -e SERVER_ID=S1 -p 127.0.0.1:5000:5000 lab-flask:v1
docker ps
docker logs flask-prueba
curl -i http://127.0.0.1:5000/health
curl -s http://127.0.0.1:5000/api/estado | python3 -m json.tool
```
Abrir en el navegador de la **VM servidor** `http://localhost:5000/`.
Para mostrar otra instancia con el mismo código:
```bash
docker stop flask-prueba
docker run -d --rm --name flask-prueba -e SERVER_ID=S2 -p 127.0.0.1:5000:5000 lab-flask:v1
curl -s http://127.0.0.1:5000/health | python3 -m json.tool
docker stop flask-prueba
```

**Nota:** publicar 127.0.0.1:5000 temporalmente en estas dos primeras fases solo permite probar el contenedor desde la propia VM. En las fases 3-5 los puertos Flask dejarán de estar publicados: Nginx será el único acceso externo por 8080.

## Script de cliente (para fase 4)
En la **VM cliente** copiar `cliente_pruebas.py` y `cliente.env.ejemplo` (renombrarlo a `cliente.env`). Ajustar solo `SERVER_IP`; luego:
```bash
python3 cliente_pruebas.py -n 30
```
No hace falta instalar Flask ni Docker en la VM cliente.
