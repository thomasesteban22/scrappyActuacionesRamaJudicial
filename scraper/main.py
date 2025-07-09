import os
# 1) Silencia TensorFlow y Chrome/DevTools
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['WEBVIEW_LOG_LEVEL']    = '3'

import time
import threading
import logging
from queue import Queue

# 2) Config global de logging: sólo INFO y superiores
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
# Silencia logs muy ruidosos
for noisy in ('selenium', 'urllib3', 'absl', 'google_apis'):
    logging.getLogger(noisy).setLevel(logging.WARNING)

from .config    import OUTPUT_DIR, NUM_THREADS
from .loader    import cargar_procesos
from .browser   import new_chrome_driver
from .worker    import worker_task
from .reporter  import generar_pdf
import scraper.worker as worker
from .config import OUTPUT_DIR, NUM_THREADS, PDF_PATH

def main():
    start_ts = time.time()

    # — Borro el PDF antiguo para forzar regeneración —
    if os.path.exists(PDF_PATH):
        os.remove(PDF_PATH)

    # Cargo procesos **solo una vez**
    procesos = cargar_procesos()
    TOTAL = len(procesos)
    worker.TOTAL_PROCESSES = TOTAL

    logging.info(f"Total de procesos a escanear: {TOTAL}")
    logging.info("=== INICIO ===")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Cola de trabajos
    q = Queue()
    for num in procesos:
        q.put(num)
    for _ in range(NUM_THREADS):
        q.put(None)

    # Arranco N drivers
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

            # Hasta 3 reintentos en el mismo tab
            for intento in range(10):
                try:
                    worker_task(numero, driver, results, actes, errors, lock)
                    break
                except Exception as exc:
                    logging.warning(f"{numero}: intento {intento+1}/10 fallido ({exc})")
                    if intento == 2:
                        with lock:
                            errors.append((numero, str(exc)))

        driver.quit()

    # Lanzo hilos
    for drv in drivers:
        t = threading.Thread(target=loop, args=(drv,), daemon=True)
        t.start()
        threads.append(t)

    # Espero a que acaben
    q.join()
    for t in threads:
        t.join()

    # Genero reporte
    generar_pdf(TOTAL, actes, errors, start_ts, time.time())

    # Resumen final
    err = len(errors)
    esc = TOTAL - err
    logging.info(f"=== RESUMEN === Total: {TOTAL} | Escaneados: {esc} | Errores: {err}")
    if err:
        logging.error("Procesos con error:")
        for num, msg in errors:
            logging.error(f"  • {num}: {msg}")
    logging.info("=== FIN TOTAL ===")


if __name__ == "__main__":
    main()
