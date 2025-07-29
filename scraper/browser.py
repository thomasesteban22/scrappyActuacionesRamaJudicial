import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from .config import HEADLESS, CHROME_BIN, CHROMEDRIVER_PATH

# Silencia logs internos de webdriver_manager
logging.getLogger('WDM').setLevel(logging.ERROR)
logging.getLogger('webdriver_manager').setLevel(logging.ERROR)

def new_chrome_driver(worker_id=None):
    opts = webdriver.ChromeOptions()
    opts.add_argument("--remote-allow-origins=*")
    opts.add_experimental_option("excludeSwitches", ["enable-automation","enable-logging"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--disable-blink-features=AutomationControlled")

    # — FORZAMOS TAMAÑO DE VENTANA tipo escritorio para evitar versión móvil/responsive —
    opts.add_argument("--window-size=1920,1080")

    # — SPOOFEA USER-AGENT de Chrome estable escritorio —
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.7204.168 Safari/537.36"
    )

    # Bloquea recursos innecesarios
    prefs = {
        "profile.managed_default_content_settings.images":      2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.fonts":       2,
    }
    opts.add_experimental_option("prefs", prefs)
    opts.add_argument("--log-level=3")

    # Headless según .env o entorno
    if HEADLESS:
        opts.add_argument("--headless")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
    else:
        opts.add_argument("--start-maximized")

    # Perfil aislado por worker
    base = os.path.join(os.getcwd(), "tmp_profiles")
    os.makedirs(base, exist_ok=True)
    stamp = worker_id or int(time.time() * 1000)
    profile_dir = os.path.join(base, f"profile_{stamp}")
    os.makedirs(profile_dir, exist_ok=True)
    opts.add_argument(f"--user-data-dir={profile_dir}")

    # Usa binario de Chrome si está instalado
    if CHROME_BIN and os.path.isfile(CHROME_BIN):
        opts.binary_location = CHROME_BIN

    # Servicio de ChromeDriver (viene de tu .env)
    svc = Service(executable_path=CHROMEDRIVER_PATH, log_path=os.devnull)

    # Suprime toda salida de stdout/stderr de ChromeDriver y DevTools
    saved_stdout = os.dup(1)
    saved_stderr = os.dup(2)
    devnull = os.open(os.devnull, os.O_RDWR)
    try:
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        driver = webdriver.Chrome(service=svc, options=opts)
    finally:
        os.dup2(saved_stdout, 1)
        os.dup2(saved_stderr, 2)
        os.close(saved_stdout)
        os.close(saved_stderr)
        os.close(devnull)

    driver.set_page_load_timeout(60)
    driver.implicitly_wait(5)
    return driver

def is_page_maintenance(driver):
    body = driver.find_element(By.TAG_NAME, "body").text.lower()
    return any(k in body for k in ("mantenimiento", "temporalmente fuera"))
