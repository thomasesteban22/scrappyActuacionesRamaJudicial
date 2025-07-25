# scraper/browser.py

import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from .config import ENV

# Silencia internamente los logs de WDM
logging.getLogger('WDM').setLevel(logging.ERROR)
logging.getLogger('webdriver_manager').setLevel(logging.ERROR)

def new_chrome_driver(worker_id=None):
    opts = webdriver.ChromeOptions()
    opts.add_argument("--remote-allow-origins=*")
    opts.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--disable-blink-features=AutomationControlled")

    # Bloquear carga de recursos innecesarios
    prefs = {
        "profile.managed_default_content_settings.images":      2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.fonts":       2,
    }
    opts.add_experimental_option("prefs", prefs)
    opts.add_argument("--log-level=3")

    if ENV.upper() == "PRODUCTION":
        opts.add_argument("--headless")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
    else:
        opts.add_argument("--start-maximized")

    # ———————————— Aísla el perfil de usuario para cada worker ————————————
    # usa tmp_profiles/profile_<worker_id>
    base = os.path.join(os.getcwd(), "tmp_profiles")
    os.makedirs(base, exist_ok=True)
    stamp = worker_id if worker_id is not None else int(time.time() * 1000)
    profile_dir = os.path.join(base, f"profile_{stamp}")
    os.makedirs(profile_dir, exist_ok=True)
    opts.add_argument(f"--user-data-dir={profile_dir}")

    svc = Service(ChromeDriverManager().install())
    # Sólo mostramos arranque en desarrollo (no headless)
    if ENV.upper() != "PRODUCTION":
        logging.info(f"Worker Chrome #{stamp} iniciado (headless={ENV.upper()=='PRODUCTION'})")
    return webdriver.Chrome(service=svc, options=opts)


def is_page_maintenance(driver):
    body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
    keywords = ("mantenimiento", "temporalmente fuera")
    return any(k in body_text for k in keywords)
