import time, random, logging, itertools
from datetime import date, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .config import DIAS_BUSQUEDA, WAIT_TIME
from .browser import is_page_maintenance
from .page_objects import ConsultaProcesosPage

process_counter = itertools.count(1)
TOTAL_PROCESSES = 0

def wait():
    time.sleep(WAIT_TIME * (1 + 0.5*random.random()))

def worker_task(numero, driver, results, actes, errors, lock):
    idx = next(process_counter)
    logging.info(f"[{idx}/{TOTAL_PROCESSES}] → {numero}")
    page = ConsultaProcesosPage(driver)
    cutoff = date.today() - timedelta(days=DIAS_BUSQUEDA)

    try:
        page.load(); wait()
        if is_page_maintenance(driver):
            logging.warning("Mantenimiento, durmiendo 30m")
            time.sleep(1800); page.load(); wait()

        page.select_por_numero(); wait()
        page.enter_numero(numero); wait()
        page.click_consultar(); wait()

        # modal múltiple
        try:
            btn = WebDriverWait(driver,5).until(
                EC.element_to_be_clickable((By.XPATH,
                  "//*[@id='app']/div[3]//button"
                ))
            )
            btn.click(); wait()
        except:
            pass

        # spans de fecha
        spans = WebDriverWait(driver,20).until(
            EC.presence_of_all_elements_located((
              By.XPATH,"//table/tbody/tr/td[3]/div/button/span"
            ))
        ); wait()

        match = None
        for s in spans:
            txt = s.text.strip()
            try:
                f = date.fromisoformat(txt)
            except:
                continue
            if f >= cutoff:
                match = s; break

        if not match:
            logging.info(f"{numero}: sin fechas ≥ cutoff")
            return

        # click fecha aceptada
        match.find_element(By.XPATH,"..").click(); wait()

        # tabla de actuaciones
        tbl = WebDriverWait(driver,20).until(
            EC.presence_of_element_located((By.XPATH,"(//table)[2]"))
        )
        WebDriverWait(driver,10).until(
            lambda d: len(tbl.find_elements(By.TAG_NAME,"tr"))>1
        ); wait()

        any_saved = False
        url = f"{ConsultaProcesosPage.URL}?numeroRadicacion={numero}"
        for row in tbl.find_elements(By.TAG_NAME,"tr")[1:]:
            cols = row.find_elements(By.TAG_NAME,"td")
            if len(cols)<3: continue
            try:
                f = date.fromisoformat(cols[0].text.strip())
            except:
                continue
            if f >= cutoff:
                any_saved = True
                with lock:
                    actes.append((
                        numero, f.isoformat(),
                        cols[1].text.strip(),
                        cols[2].text.strip(),
                        url
                    ))
        with lock:
            results.append((numero,url))

        logging.info(f"{numero}: guardadas? {any_saved}")
        page.click_volver(); wait()

    except Exception as e:
        logging.error(f"{numero}: falla → {e}")
        raise
