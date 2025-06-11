# scraper/main.py

import os
# 1) silenciar TensorFlow, DevTools y WebDriverManager
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['WEBVIEW_LOG_LEVEL']    = '3'
os.environ['WDM_LOG_LEVEL']        = '0'

import time
import threading
import logging
from queue import Queue

# 2) logging mínimo
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    force=True
)
# ocultar logs ruidosos
for noisy in ('selenium', 'urllib3', 'absl', 'google_apis', 'webdriver_manager'):
    logging.getLogger(noisy).setLevel(logging.WARNING)

from .config    import OUTPUT_DIR, NUM_THREADS
from .loader    import cargar_procesos
from .browser   import new_chrome_driver
from .worker    import worker_task
import scraper.worker as worker
from .reporter  import generar_pdf

def main():
    start_ts = time.time()

    procesos = cargar_procesos()
    TOTAL    = len(procesos)
    worker.TOTAL_PROCESSES = TOTAL

    logging.info(f"{TOTAL} procesos cargados desde Excel")
    logging.info("=== INICIO ===")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # cola y drivers…
    q = Queue()
    for num in procesos:
        q.put(num)
    for _ in range(NUM_THREADS):
        q.put(None)

    drivers = [new_chrome_driver() for _ in range(NUM_THREADS)]
    results, actes, errors = [], [], []
    lock = threading.Lock()
    threads = []

    def loop(driver):
        while True:
            numero = q.get()
            q.task_done()
            if numero is None:
                break
            # hasta 3 reintentos
            for intento in range(3):
                try:
                    worker_task(numero, driver, results, actes, errors, lock)
                    break
                except Exception as exc:
                    if intento == 2:
                        with lock:
                            errors.append((numero, str(exc)))
            # fin reintentos
        driver.quit()

    for drv in drivers:
        t = threading.Thread(target=loop, args=(drv,), daemon=True)
        t.start()
        threads.append(t)

    q.join()
    for t in threads:
        t.join()

    generar_pdf(TOTAL, actes, errors, start_ts, time.time())

    # resumen final
    err       = len(errors)
    escaneados= TOTAL - err
    logging.info(f"=== RESUMEN === Total: {TOTAL} | Escaneados: {escaneados} | Errores: {err}")
    if err:
        for num, msg in errors:
            logging.error(f"  • {num}: {msg}")
    logging.info("=== FIN TOTAL ===")


if __name__ == "__main__":
    main()
