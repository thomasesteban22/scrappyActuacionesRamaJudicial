# 1) Imagen base ligera
FROM python:3.11-slim

# 2) Variables para pip y salida sin buffer
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

# 3) Instala Chromium y su chromedriver que coincidirá en versión
RUN apt-get update && \
    apt-get install -y chromium chromium-driver && \
    rm -rf /var/lib/apt/lists/*

# 4) Directorio de trabajo
WORKDIR /app

# 5) Copia e instala dependencias
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install -r requirements.txt

# 6) Copia el resto del código de la aplicación
COPY . .

# 7) Crea carpetas necesarias
RUN mkdir -p data output tmp_profiles

# 8) Punto de entrada
ENTRYPOINT ["python", "-m", "scraper.main"]
