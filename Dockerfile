FROM python:3.11-slim

# 1) Instala Chromium y su driver
RUN apt-get update && \
    apt-get install -y chromium chromium-driver && \
    rm -rf /var/lib/apt/lists/*

# 2) Variables pip/logs
ENV PIP_NO_CACHE_DIR=1 PYTHONUNBUFFERED=1 \
    CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver

WORKDIR /app

# 3) Copia e instala reqs
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN mkdir -p data output tmp_profiles

ENTRYPOINT ["python","-m","scraper.main"]
