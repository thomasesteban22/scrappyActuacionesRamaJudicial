import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class ConsultaProcesosPage:
    URL = "https://consultaprocesos.ramajudicial.gov.co/Procesos/NumeroRadicacion"

    def __init__(self, driver, selectors_path="selectors.json"):
        self.driver = driver
        with open(selectors_path, 'r', encoding='utf-8') as f:
            self.sel = json.load(f)

    def load(self):
        self.driver.get(self.URL)
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

    def _find(self, key, timeout=20):
        for alt in self.sel.get(key, []):
            by_str, expr = alt.split(":", 1)
            by = {"xpath": By.XPATH, "css": By.CSS_SELECTOR, "tag": By.TAG_NAME}[by_str]
            try:
                el = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((by, expr))
                )
                # lo resaltamos para debugging
                self.driver.execute_script("arguments[0].style.backgroundColor='red'", el)
                return el
            except Exception:
                continue
        raise RuntimeError(f"Selector '{key}' no encontró elemento.")

    def select_por_numero(self):
        # 1) Primero intentamos con el selector custom
        try:
            radio = self._find("radio_busqueda_numero")
            radio.click()
            return
        except RuntimeError:
            pass

        # 2) Fallback: buscamos todos los radios por name y clicamos el de value correcto
        radios = self.driver.find_elements(By.NAME, "TipoBusqueda")
        for r in radios:
            if r.get_attribute("value") == "NumeroRadicacion":
                r.click()
                return
        raise RuntimeError("radio_busqueda_numero no encontrado ni por fallback.")

    def enter_numero(self, numero):
        inp = self._find("input_numero")
        inp.clear()
        inp.send_keys(numero)

    def click_consultar(self):
        self._find("btn_consultar").click()

    def click_volver(self):
        try:
            self._find("btn_volver", timeout=5).click()
        except Exception:
            pass

    def get_tablas(self):
        return WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "table"))
        )
