import os, time, logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from .config import HEADLESS

logging.getLogger('WDM').setLevel(logging.ERROR)

def new_chrome_driver(worker_id=None):
    opts = webdriver.ChromeOptions()
    # ocultar señales de automatización
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation","enable-logging"])
    # no cargar imágenes
    opts.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
    # headless según config
    if HEADLESS:
        opts.add_argument("--headless")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-dev-shm-usage")
    else:
        opts.add_argument("--start-maximized")
    # perfil aislado
    base = os.path.join(os.getcwd(), "tmp_profiles")
    os.makedirs(base, exist_ok=True)
    stamp = worker_id or int(time.time()*1000)
    prof = os.path.join(base, f"profile_{stamp}")
    os.makedirs(prof, exist_ok=True)
    opts.add_argument(f"--user-data-dir={prof}")

    # instalamos el driver coincidente
    drv_path = ChromeDriverManager().install()
    svc = Service(drv_path, log_path=os.devnull)
    driver = webdriver.Chrome(service=svc, options=opts)
    driver.set_page_load_timeout(60)
    driver.implicitly_wait(5)
    return driver

def is_page_maintenance(driver):
    txt = driver.find_element(By.TAG_NAME, "body").text.lower()
    return "mantenimiento" in txt or "temporalmente fuera" in txt
