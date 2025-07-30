import os, time, logging, threading, itertools
from queue import Queue
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from .config    import OUTPUT_DIR, NUM_THREADS, SCHEDULE_TIME
from .loader    import cargar_procesos
from .browser   import new_chrome_driver
from .worker    import worker_task, TOTAL_PROCESSES, process_counter
from .reporter  import generar_pdf
from .mailer    import send_report_email

# Logging básico
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
for lib in ('selenium','urllib3','absl','google_apis'): logging.getLogger(lib).setLevel(logging.WARNING)

def ejecutar_ciclo():
    # reinicia contador
    from .worker import process_counter, TOTAL_PROCESSES as TP
    process_counter = itertools.count(1)
    procesos = cargar_procesos()
    TOTAL_PROCESSES = len(procesos)
    logging.info(f"Total a escanear: {TOTAL_PROCESSES}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    q = Queue()
    for n in procesos: q.put(n)
    for _ in range(NUM_THREADS): q.put(None)

    drivers = [new_chrome_driver(i) for i in range(NUM_THREADS)]
    results, actes, errors = [], [], []
    lock = threading.Lock()

    def loop(driver):
        while True:
            num = q.get(); q.task_done()
            if num is None: break
            for i in range(10):
                try:
                    worker_task(num, driver, results, actes, errors, lock)
                    break
                except Exception as e:
                    logging.warning(f"{num}: retry {i+1}/10")
            # end retries
        driver.quit()

    threads = []
    for d in drivers:
        t = threading.Thread(target=loop, args=(d,), daemon=True)
        t.start(); threads.append(t)

    q.join()
    for t in threads: t.join()

    generar_pdf(TOTAL_PROCESSES, actes, errors, time.time(), time.time())
    send_report_email()
    logging.info(">>> CICLO COMPLETADO <<<")

def main():
    logging.info("Scheduler iniciado...")
    tz = ZoneInfo("America/Bogota")
    hh, mm = map(int, SCHEDULE_TIME.split(":"))
    while True:
        now = datetime.now(tz)
        target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if now >= target: target += timedelta(days=1)
        secs = (target-now).total_seconds()
        hrs = int(secs//3600)
        mins = int((secs%3600)//60)
        logging.info(f"Next run in {hrs}h {mins}m")
        time.sleep(secs)
        ejecutar_ciclo()

if __name__=="__main__":
    main()
