# 1. Base
FROM python:3.10-slim

# 2. Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 3. Directorio de trabajo
WORKDIR /app

# 4. Instala dependencias del proyecto
COPY requirements.txt .
RUN pip install -r requirements.txt

# 5. Copia el resto de tu código
#    - page_objects.py y selectors.json viven en la raíz
#    - scraper/ es tu paquete principal
#    - data/ contiene tus Excel de entrada
#    - .env con la configuración
COPY .env .
COPY page_objects.py selectors.json ./
COPY scraper/ ./scraper
COPY data/ ./data

# 6. Crea usuario no-root
RUN addgroup --system appgroup \
 && adduser --system appuser --ingroup appgroup \
 && chown -R appuser:appgroup /app
USER appuser

# 7. Punto de entrada
CMD ["python", "-m", "scraper.main"]
