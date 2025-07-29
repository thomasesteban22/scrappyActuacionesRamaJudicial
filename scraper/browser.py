# scraper/browser.py

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
    # Permitir CORS y ocultar indicadores de Selenium
    opts.add_argument("--remote-allow-origins=*")
    opts.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--disable-blink-features=AutomationControlled")

    # Bloquear recursos innecesarios
    prefs = {
        "profile.managed_default_content_settings.images":      2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.fonts":       2,
    }
    opts.add_experimental_option("prefs", prefs)
    opts.add_argument("--log-level=3")

    # Headless según configuración
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

    # Si hay un binario válido de Chrome/Chromium, lo usamos
    if CHROME_BIN and os.path.isfile(CHROME_BIN):
        opts.binary_location = CHROME_BIN

    # ─── Selección de Service ───
    # En producción (VPS/docker) siempre usamos webdriver-manager
    if ENV.lower() == "production":
        from webdriver_manager.chrome import ChromeDriverManager
        driver_path = ChromeDriverManager().install()
        svc = Service(executable_path=driver_path, log_path=os.devnull)
    else:
        # En desarrollo usamos el CHROMEDRIVER_PATH si existe, si no fallback
        if CHROMEDRIVER_PATH and os.path.isfile(CHROMEDRIVER_PATH):
            svc = Service(executable_path=CHROMEDRIVER_PATH, log_path=os.devnull)
        else:
            from webdriver_manager.chrome import ChromeDriverManager
            driver_path = ChromeDriverManager().install()
            svc = Service(executable_path=driver_path, log_path=os.devnull)

    # ─── Silenciamos la salida de ChromeDriver y del navegador ───
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

    # Timeouts y esperas por defecto
    driver.set_page_load_timeout(60)
    driver.implicitly_wait(5)

    if not HEADLESS:
        logging.info(f"➜ Chrome (worker {stamp}) headless={HEADLESS}")
    return driver

def is_page_maintenance(driver):
    body = driver.find_element(By.TAG_NAME, "body").text.lower()
    return any(k in body for k in ("mantenimiento", "temporalmente fuera"))
