import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .config import ELEMENT_TIMEOUT

class ConsultaProcesosPage:
    URL = "https://consultaprocesos.ramajudicial.gov.co/Procesos/NumeroRadicacion"

    def __init__(self, driver, path="selectors.json"):
        self.driver = driver
        with open(path, encoding="utf-8") as f:
            self.sel = json.load(f)

    def load(self):
        self.driver.get(self.URL)
        WebDriverWait(self.driver, ELEMENT_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME,"body"))
        )

    def _find(self, key, timeout=ELEMENT_TIMEOUT):
        for expr in self.sel[key]:
            by, selector = expr.split(":",1)
            by = {
                "css": By.CSS_SELECTOR,
                "xpath": By.XPATH
            }[by]
            try:
                el = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((by,selector))
                )
                return el
            except:
                continue
        raise RuntimeError(f"{key} no encontrado ni por fallback.")

    def select_por_numero(self):
        self._find("radio_busqueda_numero").click()

    def enter_numero(self, numero):
        inp = self._find("input_numero")
        inp.clear()
        inp.send_keys(numero)

    def click_consultar(self):
        self._find("btn_consultar").click()

    def click_volver(self):
        try:
            self._find("btn_volver", timeout=5).click()
        except:
            pass

    def get_tablas(self):
        return self.driver.find_elements(By.TAG_NAME, "table")
