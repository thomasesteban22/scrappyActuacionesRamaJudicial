FROM python:3.12-slim

# instalar dependencias de Chrome
RUN apt-get update && \
    apt-get install -y wget gnupg2 fonts-liberation libappindicator3-1 libasound2 \
       libatk-bridge2.0-0 libatk1.0-0 libatspi2.0-0 libcups2 libdbus-1-3 libgbm1 \
       libgtk-3-0 libnspr4 libnss3 libx11-xcb1 libxcomposite1 libxcursor1 \
       libxdamage1 libxi6 libxrandr2 libxss1 libxtst6 xdg-utils locales --no-install-recommends && \
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" \
      > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 7) COPIAR LA CARPETA output
COPY output/ ./output

# 7) COPIAR LA CARPETA data CON TU XLSM
COPY data/ ./data

COPY scraper/ ./scraper
COPY .env .env

EXPOSE 5000
CMD ["waitress-serve", "--call", "scraper.main:create_app"]
