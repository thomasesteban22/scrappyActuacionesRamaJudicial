import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from .config import ENV, HEADLESS, CHROME_BIN, CHROMEDRIVER_PATH

# Silenciar logs internos de webdriver_manager
logging.getLogger('WDM').setLevel(logging.ERROR)
logging.getLogger('webdriver_manager').setLevel(logging.ERROR)

def new_chrome_driver(worker_id=None):
    opts = webdriver.ChromeOptions()
    # permitir orígenes remotos
    opts.add_argument("--remote-allow-origins=*")
    # quitar avisos de automation
    opts.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--disable-blink-features=AutomationControlled")
    # bloquear solo imágenes y fuentes, PERMITIR CSS para que el radio se renderice
    prefs = {
        "profile.managed_default_content_settings.images":      2,
        "profile.managed_default_content_settings.fonts":       2,
    }
    opts.add_experimental_option("prefs", prefs)
    opts.add_argument("--log-level=3")

    # Headless en producción o si se fuerza
    if HEADLESS:
        opts.add_argument("--headless")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--disable-extensions")
    else:
        opts.add_argument("--start-maximized")

    # perfil aislado por worker
    base = os.path.join(os.getcwd(), "tmp_profiles")
    os.makedirs(base, exist_ok=True)
    stamp = worker_id or int(time.time() * 1000)
    profile_dir = os.path.join(base, f"profile_{stamp}")
    os.makedirs(profile_dir, exist_ok=True)
    opts.add_argument(f"--user-data-dir={profile_dir}")

    # si se definió un CHROME_BIN válido
    if CHROME_BIN and os.path.isfile(CHROME_BIN):
        opts.binary_location = CHROME_BIN

    # configurar chromedriver
    if CHROMEDRIVER_PATH and os.path.isfile(CHROMEDRIVER_PATH):
        svc = Service(executable_path=CHROMEDRIVER_PATH, log_path=os.devnull)
    else:
        from webdriver_manager.chrome import ChromeDriverManager
        drv = ChromeDriverManager().install()
        svc = Service(executable_path=drv, log_path=os.devnull)

    # arrancar ChromeDriver
    driver = webdriver.Chrome(service=svc, options=opts)
    driver.set_page_load_timeout(60)
    driver.implicitly_wait(10)

    if not HEADLESS:
        logging.info(f"➜ Chrome (worker {stamp}) headless={HEADLESS}")
    return driver

def is_page_maintenance(driver):
    body = driver.find_element(By.TAG_NAME, "body").text.lower()
    return any(k in body for k in ("mantenimiento", "temporalmente fuera"))
