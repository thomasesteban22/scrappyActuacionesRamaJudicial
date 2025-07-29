FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instalamos Chromium y Chromedriver
RUN apt-get update \
 && apt-get install -y chromium chromium-driver \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install -r requirements.txt

COPY . .

RUN mkdir -p data output tmp_profiles

# Ponemos el entrypoint
ENTRYPOINT ["python", "-m", "scraper.main"]
