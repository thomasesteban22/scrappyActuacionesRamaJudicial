# scraper/main.py

import os
import time
import threading
import logging
from queue import Queue

# 1) Silencia TensorFlow y Chrome/DevTools
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['WEBVIEW_LOG_LEVEL']    = '3'

# 2) Config global de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    force=True
)
for noisy in ('selenium', 'urllib3', 'absl', 'google_apis'):
    logging.getLogger(noisy).setLevel(logging.WARNING)

from .config    import OUTPUT_DIR, NUM_THREADS, PDF_PATH
from .loader    import cargar_procesos
from .browser   import new_chrome_driver
from .worker    import worker_task
from .reporter  import generar_pdf
import scraper.worker as worker

def main():
    start_ts = time.time()

    # Cargo procesos y ajusto total
    procesos = cargar_procesos()
    TOTAL = len(procesos)
    worker.TOTAL_PROCESSES = TOTAL

    logging.info(f"{TOTAL} procesos cargados desde Excel")
    logging.info("=== INICIO ===")

    # ----> Elimino el PDF anterior si existe, para forzar regeneración
    if os.path.exists(PDF_PATH):
        os.remove(PDF_PATH)
        logging.info(f"Archivo previo eliminado: {PDF_PATH}")

    # Aseguro que exista la carpeta de salida
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Preparo la cola de trabajo
    q = Queue()
    for num in procesos:
        q.put(num)
    for _ in range(NUM_THREADS):
        q.put(None)

    # Inicializo un driver por hilo
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

            # Hasta 3 reintentos antes de marcar error
            for intento in range(3):
                try:
                    worker_task(numero, driver, results, actes, errors, lock)
                    break
                except Exception as exc:
                    logging.warning(f"{numero} → intento {intento+1}/3 fallido: {exc}")
                    if intento == 2:
                        with lock:
                            errors.append((numero, str(exc)))

        driver.quit()
        logging.info("Driver cerrado.")

    # Lanzo los hilos
    for drv in drivers:
        t = threading.Thread(target=loop, args=(drv,), daemon=True)
        t.start()
        threads.append(t)

    # Espero a que terminen
    q.join()
    for t in threads:
        t.join()

    # Genero el PDF final
    generar_pdf(TOTAL, actes, errors, start_ts, time.time())

    # Resumen
    err = len(errors)
    escaneados = TOTAL - err
    logging.info(f"=== RESUMEN === Total: {TOTAL} | Escaneados: {escaneados} | Errores: {err}")
    if err:
        logging.info("Procesos con error:")
        for num, msg in errors:
            logging.error(f"  • {num}: {msg}")
    logging.info("=== FIN TOTAL ===")


if __name__ == "__main__":
    main()
