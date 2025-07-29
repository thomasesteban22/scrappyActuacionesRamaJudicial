import os, time, threading, logging
import itertools, smtplib
from queue import Queue
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from flask import Flask
from waitress import serve

from .config import *
from .browser import new_chrome_driver
from .loader import cargar_procesos
from .worker import worker_task, TOTAL_PROCESSES, process_counter
from .reporter import generar_pdf

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger()

def send_email(pdf_path):
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.application import MIMEApplication
    msg = MIMEMultipart()
    msg["Subject"]="Reporte Actuaciones"
    msg["From"]=EMAIL_USER; msg["To"]=EMAIL_USER
    msg.attach(MIMEText("Adjunto el reporte.", "plain"))
    with open(pdf_path,"rb") as f:
        part=MIMEApplication(f.read(),Name=os.path.basename(pdf_path))
        part.add_header("Content-Disposition","attachment",filename=os.path.basename(pdf_path))
        msg.attach(part)
    s=smtplib.SMTP_SSL("smtp.gmail.com",465)
    s.login(EMAIL_USER,EMAIL_PASS)
    s.sendmail(EMAIL_USER,[EMAIL_USER],msg.as_string())
    s.quit()
    logger.info("Correo enviado.")

def ejecutar_ciclo():
    procesos = cargar_procesos()
    TOTAL_PROCESSES = len(procesos)
    worker_task.__globals__['TOTAL_PROCESSES'] = TOTAL_PROCESSES
    process_counter.__init__(1)

    logger.info(f"Total a escanear: {TOTAL_PROCESSES}")
    start = time.time()

    q, results, actes, errors = Queue(), [], [], []
    lock = threading.Lock()
    for n in procesos: q.put(n)
    for _ in range(NUM_THREADS): q.put(None)

    drivers = [ new_chrome_driver(i) for i in range(NUM_THREADS) ]
    threads = []
    def loop(drv):
        while True:
            num = q.get(); q.task_done()
            if num is None: break
            for i in range(10):
                try:
                    worker_task(num, drv, results, actes, errors, lock)
                    break
                except Exception:
                    logger.warning(f"{num}: retry {i+1}/10")
            else:
                logger.error(f"{num}: FALLÓ 10 veces")
        drv.quit()

    for d in drivers:
        t = threading.Thread(target=loop, args=(d,), daemon=True)
        t.start(); threads.append(t)

    q.join()
    for t in threads: t.join()

    pdf = PDF_PATH
    generar_pdf(TOTAL_PROCESSES, actes, errors, start, time.time(), pdf)
    send_email(pdf)
    logger.info("Ciclo completado.")

@app.route("/")
def idx(): return "OK"

def create_app():
    return app

def scheduler():
    tz = ZoneInfo("America/Bogota")
    hh,mm = map(int,SCHEDULE_TIME.split(":"))
    while True:
        n = datetime.now(tz)
        next_run = n.replace(hour=hh,minute=mm,second=0,microsecond=0)
        if n>=next_run: next_run += timedelta(days=1)
        wait = (next_run-n).total_seconds()
        logger.info(f"Next run in {int(wait//3600)}h {int((wait%3600)//60)}m")
        time.sleep(wait)
        ejecutar_ciclo()

if __name__=="__main__":
    threading.Thread(target=scheduler,daemon=True).start()
    serve(app, host="0.0.0.0", port=5000)
