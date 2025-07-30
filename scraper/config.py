import os
from dotenv import load_dotenv
load_dotenv()

# Entorno: 'production' o 'development'
ENV = os.getenv("ENVIRONMENT", "production").lower()

# Headless en producción o si se fuerza en .env
HEADLESS = os.getenv("HEADLESS", "false").lower() in ("1","true","yes") or ENV == "production"

# Rutas de entrada / salida
EXCEL_PATH       = os.getenv(f"EXCEL_PATH_{ENV.upper()}")
PDF_PATH         = os.getenv(f"INFORMACION_PATH_{ENV.upper()}")
OUTPUT_DIR       = os.path.dirname(PDF_PATH) or "./output"

# Chrome / Chromedriver
CHROME_BIN        = os.getenv(f"CHROME_BIN_{ENV.upper()}")
CHROMEDRIVER_PATH = os.getenv(f"CHROMEDRIVER_PATH_{ENV.upper()}")

# Email
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# Parámetros de ejecución
DIAS_BUSQUEDA   = int(os.getenv("DIAS_BUSQUEDA", 5))
WAIT_TIME       = float(os.getenv("WAIT_TIME", 0.5))
ELEMENT_TIMEOUT = int(os.getenv("ELEMENT_TIMEOUT", 20))
SCHEDULE_TIME   = os.getenv("SCHEDULE_TIME", "01:00")
NUM_THREADS     = int(os.getenv("NUM_THREADS", 3))

# Log de texto para el reporte
LOG_TXT_PATH = os.path.join(OUTPUT_DIR, "report.txt")
