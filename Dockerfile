# Dockerfile

# 1) Imagen base ligera
FROM python:3.11-slim

# 2) Variables de entorno para pip, logs y rutas de Chrome/Chromedriver
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/lib/chromium/chromedriver

# 3) Directorio de trabajo
WORKDIR /app

# 4) Instalación de Chromium y dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
      chromium \
      chromium-driver \
      ca-certificates \
      fonts-liberation \
      libgtk-3-0 \
      libnss3 \
      libxss1 \
      libasound2 \
      libx11-xcb1 \
      libappindicator3-1 \
      libatk-bridge2.0-0 \
      libgbm1 \
      libatk1.0-0 \
      libdrm2 \
    && rm -rf /var/lib/apt/lists/*

# 5) Copiamos y instalamos requisitos Python
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install -r requirements.txt

# 6) Copiamos el resto del proyecto
COPY . .

# 7) Creamos las carpetas necesarias
RUN mkdir -p data output tmp_profiles

# 8) Punto de entrada
ENTRYPOINT ["python", "-m", "scraper.main"]
