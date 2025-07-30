import time, random, logging, itertools
from datetime import date, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from .config import DIAS_BUSQUEDA, WAIT_TIME
from .browser import is_page_maintenance
from .page_objects import ConsultaProcesosPage

process_counter   = itertools.count(1)
TOTAL_PROCESSES   = 0

def wait():
    extra = WAIT_TIME * 0.5 * random.random()
    time.sleep(WAIT_TIME + extra)

def worker_task(numero, driver, results, actes, errors, lock):
    idx       = next(process_counter)
    total     = TOTAL_PROCESSES or idx
    logging.info(f"[{idx}/{total}] Iniciando proceso {numero}")
    page = ConsultaProcesosPage(driver)
    cutoff = date.today() - timedelta(days=DIAS_BUSQUEDA)

    try:
        page.load(); wait()
        if is_page_maintenance(driver):
            logging.warning("Mantenimiento detectado; duermo 30m")
            time.sleep(1800); page.load(); wait()

        page.select_por_numero(); wait()
        page.enter_numero(numero); wait()
        page.click_consultar(); wait()

        # cerrar modal multiplex si aparece
        try:
            btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//*[@id='app']/div[3]//button"))
            )
            driver.execute_script("arguments[0].style.backgroundColor='red'", btn)
            btn.click(); wait()
            logging.info(f"{numero}: modal cerrado")
        except TimeoutException:
            pass

        # spans de fecha
        spans = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.XPATH,
                "//*[@id='mainContent']//table/tbody/tr/td[3]/div/button/span"
            ))
        ); wait()

        match = None
        for s in spans:
            try:
                f = date.fromisoformat(s.text.strip())
            except:
                continue
            if f >= cutoff:
                match = s; break

        if not match:
            logging.info(f"{numero}: sin fechas ≥ cutoff")
            return

        btn = match.find_element(By.XPATH, "..")
        btn.click(); wait()

        table = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "/html/body//table"))
        )
        WebDriverWait(driver, 10).until(
            lambda d: len(table.find_elements(By.TAG_NAME, "tr")) > 1
        ); wait()

        any_saved = False
        url_link = f"{ConsultaProcesosPage.URL}?numeroRadicacion={numero}"

        for row in table.find_elements(By.TAG_NAME, "tr")[1:]:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) < 3: continue
            try:
                fa = date.fromisoformat(cols[0].text.strip())
            except:
                continue
            if fa >= cutoff:
                any_saved = True
                actu = cols[1].text.strip()
                anot = cols[2].text.strip()
                with lock:
                    actes.append((numero, fa.isoformat(), actu, anot, url_link))

        with lock:
            results.append((numero, url_link))

        logging.info(f"{numero}: guardadas actuaciones={any_saved}")
        page.click_volver(); wait()

    except Exception as e:
        logging.error(f"{numero}: falla → {e}")
        raise
