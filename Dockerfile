WORKDIR /app

# Paso 1: instalamos deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Paso 2: copiamos selectores y datos de Excel
COPY selectors.json .
COPY data/ ./data

# Paso 3: copiamos el scraper
COPY scraper/ ./scraper

# Exponemos y arrancamos
CMD ["python", "-m", "scraper.main"]
