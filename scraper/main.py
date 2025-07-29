import os, csv, smtplib, time, threading, logging, itertools
from queue import Queue
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# Silencia TF y DevTools
os.environ['TF_CPP_MIN_LOG_LEVEL']='3'
os.environ['WEBVIEW_LOG_LEVEL']='3'
os.environ['ABSL_LOG_LEVEL']='3'

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
for n in ('selenium','urllib3','absl','WDM','webdriver_manager'):
    logging.getLogger(n).setLevel(logging.WARNING)

from .config import OUTPUT_DIR, NUM_THREADS, PDF_PATH, EMAIL_USER, EMAIL_PASS, SCHEDULE_TIME
from .loader import cargar_procesos
from .browser import new_chrome_driver
from .worker import worker_task, TOTAL_PROCESSES as _TOTAL
from .reporter import generar_pdf

def exportar_csv(actes, start_ts):
    fecha = date.fromtimestamp(start_ts).isoformat()
    p = os.path.join(OUTPUT_DIR, "actuaciones.csv")
    with open(p,"w",newline="",encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["idInterno","quienRegistro","fechaRegistro","fechaEstado","etapa","actuacion","observacion"])
        for num,fe,ac,an,u in actes:
            w.writerow([num,"Sistema",fecha,fe,"",ac,an])
    logging.info(f"CSV: {p}")

def send_email():
    now = datetime.now().strftime("%A %d-%m-%Y %I:%M %p")
    smtp = smtplib.SMTP_SSL("smtp.gmail.com",465)
    smtp.login(EMAIL_USER,EMAIL_PASS)
    msg = MIMEMultipart(); msg["From"]=EMAIL_USER; msg["To"]=EMAIL_USER
    msg["Subject"]="Reporte Diario de Actuaciones"
    msg.attach(MIMEText(f"Reporte generado: {now}","plain"))
    with open(PDF_PATH,"rb") as f:
        part=MIMEApplication(f.read(),Name=os.path.basename(PDF_PATH))
    part.add_header("Content-Disposition","attachment",filename=os.path.basename(PDF_PATH))
    msg.attach(part)
    smtp.sendmail(EMAIL_USER,[EMAIL_USER],msg.as_string())
    smtp.quit()
    logging.info("Correo enviado.")

def ejecutar_ciclo():
    # reinicia contador
    from .worker import process_counter
    process_counter = itertools.count(1)
    start = time.time()
    if os.path.exists(PDF_PATH): os.remove(PDF_PATH)
    csv_old=os.path.join(OUTPUT_DIR,"actuaciones.csv")
    if os.path.exists(csv_old): os.remove(csv_old)

    procesos = cargar_procesos()
    TOTAL = len(procesos)
    from .worker import TOTAL_PROCESSES
    globals()['_TOTAL'] = TOTAL
    logging.info(f"Total a escanear: {TOTAL}")
    logging.info(">>> INICIO DE CICLO <<<")
    os.makedirs(OUTPUT_DIR,exist_ok=True)

    q=Queue()
    for n in procesos: q.put(n)
    for _ in range(NUM_THREADS): q.put(None)

    drivers=[new_chrome_driver(i) for i in range(NUM_THREADS)]
    results, actes, errors = [], [], []
    lock = threading.Lock()
    threads=[]

    def loop(driver):
        while True:
            n=q.get(); q.task_done()
            if n is None: break
            for i in range(10):
                try:
                    worker_task(n, driver, results, actes, errors, lock)
                    break
                except Exception as e:
                    logging.warning(f"{n}: intento {i+1} fallido ({e})")
                    if i==9:
                        with lock: errors.append((n,str(e)))
        driver.quit()

    for d in drivers:
        t=threading.Thread(target=loop,args=(d,),daemon=True)
        t.start(); threads.append(t)

    q.join()
    for t in threads: t.join()

    generar_pdf(TOTAL, actes, errors, start, time.time())
    exportar_csv(actes, start)
    try: send_email()
    except Exception as e: logging.error(f"Mail: {e}")

    err=len(errors); esc=TOTAL-err
    logging.info(f"=== RESUMEN: {TOTAL} esc:{esc} err:{err} ===")
    logging.info(">>> FIN CICLO <<<\n")

def main():
    logging.info("Scheduler iniciado...")
    tz=ZoneInfo("America/Bogota")
    hh,mm=map(int,SCHEDULE_TIME.split(":"))
    while True:
        now=datetime.now(tz)
        tgt=now.replace(hour=hh,minute=mm,second=0,microsecond=0)
        if now>=tgt: tgt+=timedelta(days=1)
        rem=(tgt-now).total_seconds()
        # avisos cada hora, luego minutos
        while rem>0:
            if rem>3600:
                h=int(rem//3600)
                logging.info(f"Faltan {h}h para ejecutar")
                time.sleep(3600); rem-=3600
            else:
                m=int(rem//60); s=int(rem%60)
                logging.info(f"Faltan {m}m {s}s para ejecutar")
                time.sleep(rem); rem=0
        ejecutar_ciclo()

if __name__=="__main__":
    main()
