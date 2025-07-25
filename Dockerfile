# Dockerfile

# 1) Base ligera
FROM python:3.11-slim

# 2) Variables para pip y logs
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    # Rutas donde apt instalará Chromium y Chromedriver
    CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver

# 3) Instala Chromium + Chromedriver y limpia cache de apt
RUN apt-get update \
    && apt-get install -y chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# 4) Directorio de trabajo
WORKDIR /app

# 5) Copia e instala requirements
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install -r requirements.txt

# 6) Copia el resto del proyecto
COPY . .

# 7) Crea carpetas necesarias
RUN mkdir -p data output tmp_profiles

# 8) Punto de entrada
ENTRYPOINT ["python", "-m", "scraper.main"]
