# Imagen oficial de Python: misma base para las tres instancias.
FROM python:3.12-slim

# Directorio del programa en el contenedor.
WORKDIR /app

# Instalar primero las dependencias para reutilizar la capa en nuevas builds.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Incorporar la aplicación Flask original adaptada.
COPY app.py metrics.py ./

# Valores predeterminados (cada contenedor define SERVER_ID por separado).
ENV PYTHONUNBUFFERED=1 \
    PORT=5000
EXPOSE 5000

# Iniciar la aplicación; el identificador proviene de la variable de entorno.
CMD ["python", "app.py"]
