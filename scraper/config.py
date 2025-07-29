import os
from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("ENVIRONMENT", "production").lower()
HEADLESS = os.getenv("HEADLESS", "false").lower() in ("1","true","yes") or ENV == "production"

EXCEL_PATH = os.getenv(f"EXCEL_PATH_{ENV.upper()}")
PDF_PATH   = os.getenv(f"INFORMACION_PATH_{ENV.upper()}")

CHROME_BIN        = os.getenv("CHROME_BIN")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH")

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

DIAS_BUSQUEDA   = int(os.getenv("DIAS_BUSQUEDA", 1))
WAIT_TIME       = float(os.getenv("WAIT_TIME", 2))
ELEMENT_TIMEOUT = int(os.getenv("ELEMENT_TIMEOUT", 60))
SCHEDULE_TIME   = os.getenv("SCHEDULE_TIME", "01:00")
NUM_THREADS     = int(os.getenv("NUM_THREADS", 3))

OUTPUT_DIR   = os.path.dirname(PDF_PATH) or "./output"
LOG_TXT_PATH = os.path.join(OUTPUT_DIR, "report.txt")
