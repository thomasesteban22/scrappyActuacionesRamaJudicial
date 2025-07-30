import os, time, threading, logging, itertools
from queue import Queue
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from .config import (
    OUTPUT_DIR, PDF_PATH, EXCEL_PATH, EMAIL_USER, EMAIL_PASS,
    SCHEDULE_TIME, NUM_THREADS, DIAS_BUSQUEDA
)
from .browser import new_chrome_driver
from .page_objects import ConsultaProcesosPage
from .worker import worker_task, TOTAL_PROCESSES, process_counter
from .loader import cargar_procesos
from .reporter import generar_pdf
from .mailer import send_report_email  # extrae función de envío a módulo propio

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
for noisy in ('selenium','urllib3','absl','google_apis'):
    logging.getLogger(noisy).setLevel(logging.WARNING)

def health_check():
    """Verifica carga de página antes de arrancar todo."""
    logger = logging.getLogger()
    logger.info("🔍 Verificando que la página cargue correctamente...")
    driver = new_chrome_driver()
    page = ConsultaProcesosPage(driver)
    try:
        page.load()
        logger.info("✅ Página cargó correctamente. Continuando.")
    except Exception as e:
        logger.error(f"❌ No se pudo cargar la página de consultas: {e}")
        driver.quit()
        return False
    driver.quit()
    return True

def ejecutar_ciclo():
    worker_task_counter = itertools.count(1)
    start_ts = time.time()
    # limpia viejos
    if os.path.exists(PDF_PATH): os.remove(PDF_PATH)
    # carga
    procesos = cargar_procesos()
    TOTAL = len(procesos)
    globals()['TOTAL_PROCESSES'] = TOTAL
    logging.info(f"Total a escanear: {TOTAL}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    q = Queue()
    for num in procesos: q.put(num)
    for _ in range(NUM_THREADS): q.put(None)

    drivers = [new_chrome_driver(i) for i in range(NUM_THREADS)]
    results, actes, errors = [], [], []
    lock = threading.Lock()

    def loop(driver):
        while True:
            numero = q.get(); q.task_done()
            if numero is None: break
            for intento in range(10):
                try:
                    worker_task(numero, driver, results, actes, errors, lock)
                    break
                except Exception as exc:
                    logging.warning(f"{numero}: retry {intento+1}/10")
            # fin intentos
        driver.quit()

    threads = []
    for drv in drivers:
        t = threading.Thread(target=loop, args=(drv,), daemon=True)
        t.start(); threads.append(t)
    q.join()
    for t in threads: t.join()

    generar_pdf(TOTAL, actes, errors, start_ts, time.time())
    # exportar_csv(...) si lo usas
    send_report_email()
    logging.info(">>> Fin de ciclo <<<\n")

def main():
    if not health_check():
        logging.error("Abortando aplicación: fallo en health check.")
        return
    # scheduler
    logging.info("Scheduler iniciado, esperando el primer ciclo diario...")
    tz = ZoneInfo("America/Bogota")
    hh, mm = map(int, SCHEDULE_TIME.split(":"))
    while True:
        now = datetime.now(tz)
        target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if now >= target: target += timedelta(days=1)
        wait = (target-now).total_seconds()
        hrs = int(wait//3600); mins = int((wait%3600)//60)
        logging.info(f"Next run in {hrs}h {mins}m")
        time.sleep(wait)
        ejecutar_ciclo()

if __name__=="__main__":
    main()
