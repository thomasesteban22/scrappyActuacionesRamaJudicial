# scraper/browser.py

import os
import time
import logging
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from .config import ENV, HEADLESS, CHROME_BIN, CHROMEDRIVER_PATH

# Silenciar logs internos de webdriver_manager
logging.getLogger('WDM').setLevel(logging.ERROR)
logging.getLogger('webdriver_manager').setLevel(logging.ERROR)

def _get_chrome_version(binary_path: str) -> str | None:
    """Ejecuta '<binary_path> --version' y devuelve la versión 'X.Y.Z.W' o None."""
    try:
        out = subprocess.run(
            [binary_path, '--version'],
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        # Suele venir como "Chromium 138.0.7204.168"
        parts = out.split()
        if len(parts) >= 2:
            return parts[1]
    except Exception:
        pass
    return None

def new_chrome_driver(worker_id=None):
    opts = webdriver.ChromeOptions()
    opts.add_argument("--remote-allow-origins=*")
    opts.add_experimental_option("excludeSwitches", ["enable-automation","enable-logging"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--log-level=3")
    # Bloquear recursos
    prefs = {
        "profile.managed_default_content_settings.images":      2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.fonts":       2,
    }
    opts.add_experimental_option("prefs", prefs)

    # Headless si procede
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

    # Si tenemos binario de Chrome/Chromium, lo usamos
    if CHROME_BIN and os.path.isfile(CHROME_BIN):
        opts.binary_location = CHROME_BIN

    # ─── Preparar Service ───
    # Siempre usar webdriver-manager en producción para alinear versiones
    if ENV.lower() == "production":
        from webdriver_manager.chrome import ChromeDriverManager
        # Intentar obtener la versión exacta de Chromium
        version = None
        if opts.binary_location:
            version = _get_chrome_version(opts.binary_location)
        if version:
            driver_path = ChromeDriverManager(version=version).install()
        else:
            driver_path = ChromeDriverManager().install()
        svc = Service(executable_path=driver_path, log_path=os.devnull)
    else:
        # En desarrollo, permite usar CHROMEDRIVER_PATH si es válido
        if CHROMEDRIVER_PATH and os.path.isfile(CHROMEDRIVER_PATH):
            svc = Service(executable_path=CHROMEDRIVER_PATH, log_path=os.devnull)
        else:
            from webdriver_manager.chrome import ChromeDriverManager
            driver_path = ChromeDriverManager().install()
            svc = Service(executable_path=driver_path, log_path=os.devnull)

    # ─── Suprimir toda la salida de los procesos hijos ───
    saved_stdout = os.dup(1)
    saved_stderr = os.dup(2)
    devnull = os.open(os.devnull, os.O_RDWR)
    try:
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        driver = webdriver.Chrome(service=svc, options=opts)
    finally:
        # Restaurar stdout/stderr
        os.dup2(saved_stdout, 1)
        os.dup2(saved_stderr, 2)
        os.close(saved_stdout)
        os.close(saved_stderr)
        os.close(devnull)

    # Configurar timeouts
    driver.set_page_load_timeout(60)
    driver.implicitly_wait(5)

    if not HEADLESS:
        logging.info(f"➜ Chrome (worker {stamp}) headless={HEADLESS}")
    return driver

def is_page_maintenance(driver):
    body = driver.find_element(By.TAG_NAME, "body").text.lower()
    return any(k in body for k in ("mantenimiento", "temporalmente fuera"))
