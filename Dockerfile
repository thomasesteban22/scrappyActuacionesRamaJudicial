# Dockerfile

# 1) Imagen base ligera
FROM python:3.11-slim

# 2) Variables de entorno para pip y logs
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

# 3) Directorio de trabajo
WORKDIR /app

# 4) Copiamos y instalamos requisitos
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install -r requirements.txt

# 5) Copiamos el resto del proyecto
COPY . .

# 6) Creamos carpetas para datos de entrada y salida
RUN mkdir -p data output

# 7) Punto de entrada
ENTRYPOINT ["python", "-m", "scraper.main"]
