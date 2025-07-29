import time
import random
import logging
import itertools
from datetime import date, timedelta

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from .config import DIAS_BUSQUEDA, WAIT_TIME, ELEMENT_TIMEOUT
from .browser import is_page_maintenance
from page_objects import ConsultaProcesosPage

process_counter = itertools.count(1)
TOTAL_PROCESSES = 0

def wait():
    extra = WAIT_TIME * 0.5 * random.random()
    time.sleep(WAIT_TIME + extra)

def worker_task(numero, driver, results, actes, errors, lock):
    idx = next(process_counter)
    total = TOTAL_PROCESSES or idx
    logging.info(f"[{idx}/{total}] Iniciando proceso {numero}")
    page = ConsultaProcesosPage(driver)
    cutoff = date.today() - timedelta(days=DIAS_BUSQUEDA)

    try:
        # 1) cargo página y espero body
        page.load()
        wait()

        if is_page_maintenance(driver):
            logging.warning("Mantenimiento detectado; duermo 30m")
            time.sleep(1800)
            page.load()
            wait()

        # 2) espero explícitamente radio NUMERO
        WebDriverWait(driver, ELEMENT_TIMEOUT).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR,
                "input[type=radio][name=TipoBusqueda][value=NumeroRadicacion]"
            ))
        )
        page.select_por_numero()
        wait()

        # 3) numero y 4) consultar
        page.enter_numero(numero)
        wait()
        page.click_consultar()
        wait()

        # 4.a) cierro modal si aparece
        try:
            volver = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//*[@id='app']/div[3]//button"
                ))
            )
            volver.click(); wait()
        except TimeoutException:
            pass

        # 5) espero spans de fecha
        fecha_xpath = "//*[@id='mainContent']//table/tbody/tr/td[3]/div/button/span"
        spans = WebDriverWait(driver, ELEMENT_TIMEOUT).until(
            EC.presence_of_all_elements_located((By.XPATH, fecha_xpath))
        )
        wait()

        # 6) busco primera ≥ cutoff
        match = None
        for s in spans:
            txt=s.text.strip()
            try: f=date.fromisoformat(txt)
            except: continue
            if f>=cutoff:
                match=s; break

        if not match:
            logging.info(f"{numero}: sin fechas ≥ {cutoff}")
            return

        # 7) clic en su padre
        btn=match.find_element(By.XPATH,"..")
        driver.execute_script("arguments[0].scrollIntoView()",btn)
        btn.click(); wait()

        # 8) espero tabla
        tbl_xpath="/html/body//table"
        table=WebDriverWait(driver, ELEMENT_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH,tbl_xpath))
        )
        WebDriverWait(driver,10).until(
            lambda d: len(table.find_elements(By.TAG_NAME,"tr"))>1
        )
        wait()

        # 9) extraigo filas
        any_saved=False
        url=f"{ConsultaProcesosPage.URL}?numeroRadicacion={numero}"
        for row in table.find_elements(By.TAG_NAME,"tr")[1:]:
            cols=row.find_elements(By.TAG_NAME,"td")
            if len(cols)<3: continue
            try: fact=date.fromisoformat(cols[0].text.strip())
            except: continue
            if fact>=cutoff:
                actu=cols[1].text.strip()
                anot=cols[2].text.strip()
                any_saved=True
                with lock:
                    actes.append((numero,fact.isoformat(),actu,anot,url))

        with lock:
            results.append((numero,url))

        logging.info(f"{numero}: guardadas actuaciones? {any_saved}")

        # 10) vuelvo
        page.click_volver()
        wait()

    except TimeoutException as te:
        logging.error(f"{numero}: TIMEOUT → {te}")
        raise
    except Exception as e:
        logging.error(f"{numero}: ERROR → {e}")
        raise
