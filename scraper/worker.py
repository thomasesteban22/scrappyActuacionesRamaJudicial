# scraper/worker.py

import time
import random
import logging
import itertools
from datetime import date, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

from .config import DIAS_BUSQUEDA, WAIT_TIME
from .browser import is_page_maintenance
from page_objects import ConsultaProcesosPage

process_counter = itertools.count(1)
TOTAL_PROCESSES = 0  # se asigna en main.py

def wait():
    """Pausa WAIT_TIME con hasta 50% de jitter."""
    extra = WAIT_TIME * 0.5 * random.random()
    time.sleep(WAIT_TIME + extra)

def wait_page_ready(driver, timeout=15):
    """Espera a que document.readyState sea 'complete'."""
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )

def worker_task(numero, driver, results, actes, errors, lock):
    idx       = next(process_counter)
    total     = TOTAL_PROCESSES or idx
    remaining = total - idx
    print(f"[{idx}/{total}] Proceso {numero} → Iniciando (quedan {remaining})")
    logging.info(f"[{idx}/{total}] Iniciando proceso {numero}; faltan {remaining}")

    page   = ConsultaProcesosPage(driver)
    cutoff = date.today() - timedelta(days=DIAS_BUSQUEDA)

    try:
        # 1) Cargo la página principal
        page.load()
        wait_page_ready(driver)            # ← espera a que acabe de cargar
        wait()

        # 1.a) Mantenimiento
        if is_page_maintenance(driver):
            logging.warning("Mantenimiento detectado; durmiendo 30 min")
            time.sleep(1800)
            page.load()
            wait_page_ready(driver)
            wait()

        # 2) Selecciono “Todos los Procesos”
        page.select_por_numero()
        wait_page_ready(driver)
        wait()

        # 3) Ingreso número de radicación
        page.enter_numero(numero)
        wait()

        # 4) Clic en “Consultar”
        page.click_consultar()
        wait_page_ready(driver)            # ← importante después de un submit
        wait()

        # 4.a) Modal “Volver” de múltiples registros
        try:
            volver_modal = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//*[@id='app']/div[3]/div/div/div[2]/div/button/span"
                ))
            )
            volver_modal.click()
            wait_page_ready(driver)
            wait()
            logging.info(f"{numero}: modal múltiple detectado, cerrado")
        except TimeoutException:
            pass

        # 5) Espero a que los spans de fecha estén presentes y sean estables
        xpath_fecha = (
            "//*[@id='mainContent']/div/div/div/div[2]/div/"
            "div/div[2]/div/table/tbody/tr/td[3]/div/button/span"
        )
        # Primera espera a que haya al menos 1 span
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, xpath_fecha))
        )

        # Ahora esperamos hasta que el número de spans deje de cambiar
        prev_count = -1
        stable_tries = 0
        while stable_tries < 3:
            spans = driver.find_elements(By.XPATH, xpath_fecha)
            if len(spans) == prev_count:
                stable_tries += 1
            else:
                prev_count = len(spans)
                stable_tries = 0
            time.sleep(0.5)
        if not spans:
            logging.error(f"{numero}: no encontró spans de fecha → skip")
            return

        # 6) Comparo cada fecha vs cutoff
        match_span = None
        for s in spans:
            texto = s.text.strip()
            try:
                fecha_obj = date.fromisoformat(texto)
            except ValueError:
                continue

            driver.execute_script("arguments[0].style.backgroundColor='red'", s)
            decision = "ACEPTADA" if fecha_obj >= cutoff else "RECHAZADA"
            logging.info(f"{numero}: fecha {fecha_obj} vs {cutoff} → {decision}")

            if fecha_obj >= cutoff:
                match_span = s
                break

        if not match_span:
            logging.info(f"{numero}: ninguna fecha en rango → salto")
            return

        # 7) Clic en el <button> padre del span aceptado
        btn = match_span.find_element(By.XPATH, "..")
        driver.execute_script("arguments[0].scrollIntoView()", btn)
        btn.click()
        wait_page_ready(driver)
        wait()

        # 8) Localizo la tabla de actuaciones (espera robusta)
        table_xpath = (
            "/html/body/div/div[1]/div[3]/main/div/div/div/div[2]/div/"
            "div/div[2]/div[2]/div[2]/div/div/div[2]/div/div[1]/div[2]/div/table"
        )
        actuaciones_table = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, table_xpath))
        )
        wait()

        # 9) Recorro y guardo cada actuación en rango, con retry ante StaleElement
        rows = actuaciones_table.find_elements(By.TAG_NAME, "tr")[1:]
        url_link = f"{ConsultaProcesosPage.URL}?numeroRadicacion={numero}"
        any_saved = False

        for _ in range(3):  # hasta 3 intentos en caso de Stale
            try:
                for fila in rows:
                    cds = fila.find_elements(By.TAG_NAME, "td")
                    if len(cds) < 3:
                        continue
                    fecha_act = date.fromisoformat(cds[0].text.strip())
                    if fecha_act >= cutoff:
                        any_saved = True
                        cds_text = (fecha_act.isoformat(),
                                    cds[1].text.strip(),
                                    cds[2].text.strip())
                        with lock:
                            actes.append((numero, *cds_text, url_link))
                break
            except StaleElementReferenceException:
                time.sleep(0.5)
                rows = actuaciones_table.find_elements(By.TAG_NAME, "tr")[1:]

        # 10) Registro URL y confirmo guardado
        with lock:
            results.append((numero, url_link))

        if any_saved:
            logging.info(f"{numero}: proceso completado con actuaciones guardadas")
        else:
            logging.info(f"{numero}: proceso completado sin actuaciones en rango")

        # 11) Vuelvo al listado
        page.click_volver()
        wait_page_ready(driver)
        wait()

    except Exception as e:
        logging.error(f"{numero} → ERROR general: {e}")
        with lock:
            errors.append((numero, str(e)))
