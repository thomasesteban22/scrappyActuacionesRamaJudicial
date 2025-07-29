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

# Reiniciado en cada ciclo
process_counter = itertools.count(1)
TOTAL_PROCESSES = 0  # asignado desde main

def wait():
    """Pausa WAIT_TIME ±50% jitter."""
    extra = WAIT_TIME * 0.5 * random.random()
    time.sleep(WAIT_TIME + extra)

def worker_task(numero, driver, results, actes, errors, lock):
    idx       = next(process_counter)
    total     = TOTAL_PROCESSES or idx
    remaining = total - idx
    logging.info(f"[{idx}/{total}] Iniciando proceso {numero}")

    page   = ConsultaProcesosPage(driver)
    cutoff = date.today() - timedelta(days=DIAS_BUSQUEDA)

    try:
        # 1) Cargo página
        page.load()
        wait()

        # 1.a) Si mantenimiento, duermo 30m y recargo
        if is_page_maintenance(driver):
            logging.warning("Mantenimiento detectado; durmiendo 30 minutos")
            time.sleep(1800)
            page.load()
            wait()

        # 1.b) ESPERA explícita del radio antes de clicar
        WebDriverWait(driver, ELEMENT_TIMEOUT).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR,
                "input[type=radio][name=TipoBusqueda][value=NumeroRadicacion]"
            ))
        )

        # 2) Selecciono “Número de Radicación”
        page.select_por_numero()
        wait()

        # 3) Ingreso número
        page.enter_numero(numero)
        wait()

        # 4) Clic “Consultar”
        page.click_consultar()
        wait()

        # 4.a) Cierra modal múltiple si aparece
        try:
            volver_modal = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//*[@id='app']/div[3]//button"
                ))
            )
            volver_modal.click()
            wait()
            logging.info(f"{numero}: modal múltiple detectado y cerrado")
        except TimeoutException:
            pass

        # 5) Espero a que aparezcan los spans de fecha
        xpath_fecha = (
            "//*[@id='mainContent']//table/tbody/tr/td[3]/div/button/span"
        )
        spans = WebDriverWait(driver, ELEMENT_TIMEOUT).until(
            EC.presence_of_all_elements_located((By.XPATH, xpath_fecha))
        )
        wait()

        # 6) Busco el primer span con fecha ≥ cutoff
        match_span = None
        for s in spans:
            txt = s.text.strip()
            try:
                f = date.fromisoformat(txt)
            except ValueError:
                continue
            if f >= cutoff:
                match_span = s
                break

        if not match_span:
            logging.info(f"{numero}: ninguna fecha ≥ {cutoff} → skip")
            return

        # 7) Clico su botón padre
        btn = match_span.find_element(By.XPATH, "..")
        driver.execute_script("arguments[0].scrollIntoView()", btn)
        btn.click()
        wait()

        # 8) Espero la tabla de actuaciones y al menos una fila de datos
        table_xpath = "/html/body//table"
        table = WebDriverWait(driver, ELEMENT_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, table_xpath))
        )
        WebDriverWait(driver, 10).until(
            lambda d: len(table.find_elements(By.TAG_NAME, "tr")) > 1
        )
        wait()

        # 9) Recojo cada actuación en rango
        any_saved = False
        url_link  = f"{ConsultaProcesosPage.URL}?numeroRadicacion={numero}"
        for row in table.find_elements(By.TAG_NAME, "tr")[1:]:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) < 3:
                continue
            try:
                fact = date.fromisoformat(cols[0].text.strip())
            except ValueError:
                continue
            if fact >= cutoff:
                actu = cols[1].text.strip()
                anot = cols[2].text.strip()
                any_saved = True
                with lock:
                    actes.append((numero, fact.isoformat(), actu, anot, url_link))

        # 10) Registro URL
        with lock:
            results.append((numero, url_link))

        logging.info(f"{numero}: actuaciones guardadas? {any_saved}")

        # 11) Vuelvo al listado
        page.click_volver()
        wait()

    except TimeoutException as te:
        logging.error(f"{numero}: TIMEOUT → {te}")
        raise
    except Exception as e:
        logging.error(f"{numero}: ERROR → {e}")
        raise
