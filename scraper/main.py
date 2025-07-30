# scraper/main.py

import logging
import threading
import time
import os
from queue import Queue
from datetime import datetime

from .loader import cargar_procesos
from .worker import worker_task, process_counter
from .browser import new_chrome_driver, is_page_maintenance
from .page_objects import ConsultaProcesosPage
from .reporter import generar_pdf

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Número de hilos simultáneos de scraping
NUM_WORKERS = 4

# Carpeta donde volcamos CSVs, capturas y demás
OUTPUT_DIR = "./output"


def ejecutar_ciclo():
    """
    Ejecuta un ciclo completo de:
      1) Prueba de carga de la página principal.
      2) Lectura de radicaciones desde Excel.
      3) Procesamiento en paralelo con retries.
      4) Generación de PDF y log de texto.
    """
    # --- 1) Prueba de carga de la página principal
    driver = new_chrome_driver("check")
    logging.info("▶ Probando carga de la página principal...")
    try:
        page = ConsultaProcesosPage(driver)
        page.load()
        if is_page_maintenance(driver):
            logging.error("✖ La página está en mantenimiento. Abortando ciclo.")
            return
        logging.info("✔ Página cargada correctamente.")
    except Exception as e:
        logging.error(f"✖ Error al cargar la página de consulta: {e}")
        return
    finally:
        driver.quit()

    # --- 2) Cargo las radicaciones a escanear
    procesos = cargar_procesos()
    total = len(procesos)
    logging.info(f"Total a escanear: {total}")

    # Preparo el directorio de salida
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --- 3) Pongo la cola y lanzo los workers
    q = Queue()
    for numero in procesos:
        q.put(numero)

    def _worker():
        while True:
            num = q.get()
            for intento in range(10):
                try:
                    worker_task(num)
                    break
                except Exception as e:
                    logging.warning(f"{num}: retry {intento+1}/10 → {e}")
                    time.sleep(1)
            q.task_done()

    # Lanzo los hilos
    for _ in range(NUM_WORKERS):
        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    # Espero a que termine todo
    q.join()

    # --- 4) Genero el PDF y el log de texto
    generar_pdf(
        total_procesos=total,
        actes=process_counter.actes,
        errors=process_counter.errors,
        start_ts=process_counter.start_ts,
        end_ts=time.time()
    )
    logging.info(">>> CICLO COMPLETADO <<<")


def scheduler():
    """
    Corre ejecutar_ciclo() una vez al arrancar y luego
    cada 24 h automáticamente.
    """
    # Primera corrida inmediata
    logging.info("Next run in 0h 0m")
    while True:
        ejecutar_ciclo()
        # calculo horas/minutos para el próximo run
        horas = 24
        minutos = 0
        logging.info(f"Next run in {horas}h {minutos}m")
        time.sleep(24 * 3600)


if __name__ == "__main__":
    # Arranco el scheduler en background
    t = threading.Thread(target=scheduler, name="scheduler", daemon=True)
    t.start()

    # Arranco la API con Waitress
    from waitress import serve
    from .app import app   # tu flask app

    logging.info("Serving on http://0.0.0.0:5000")
    serve(app, host="0.0.0.0", port=5000)
