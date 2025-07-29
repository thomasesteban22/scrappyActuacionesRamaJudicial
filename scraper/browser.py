# scraper/browser.py

import os, time, logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from .config import HEADLESS, CHROME_BIN, CHROMEDRIVER_PATH

logging.getLogger('WDM').setLevel(logging.ERROR)
logging.getLogger('webdriver_manager').setLevel(logging.ERROR)

def new_chrome_driver(worker_id=None):
    opts = webdriver.ChromeOptions()
    opts.add_argument("--remote-allow-origins=*")
    opts.add_experimental_option("excludeSwitches", ["enable-automation","enable-logging"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("prefs", {
        "profile.managed_default_content_settings.images":      2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.fonts":       2,
    })
    opts.add_argument("--log-level=3")

    if HEADLESS:
        opts.add_argument("--headless")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
    else:
        opts.add_argument("--start-maximized")

    # Perfil aislado
    base = os.path.join(os.getcwd(), "tmp_profiles")
    os.makedirs(base, exist_ok=True)
    stamp = worker_id or int(time.time()*1000)
    profile = os.path.join(base, f"profile_{stamp}")
    os.makedirs(profile, exist_ok=True)
    opts.add_argument(f"--user-data-dir={profile}")

    # Forzamos binario y driver de APT
    if CHROME_BIN and os.path.isfile(CHROME_BIN):
        opts.binary_location = CHROME_BIN
    svc = Service(executable_path=CHROMEDRIVER_PATH, log_path=os.devnull)

    # suprimimos salida de DevTools / absl / TF…
    saved_out, saved_err = os.dup(1), os.dup(2)
    devnull = os.open(os.devnull, os.O_RDWR)
    os.dup2(devnull,1); os.dup2(devnull,2)
    try:
        driver = webdriver.Chrome(service=svc, options=opts)
    finally:
        os.dup2(saved_out,1); os.dup2(saved_err,2)
        os.close(saved_out); os.close(saved_err); os.close(devnull)

    driver.set_page_load_timeout(60)
    driver.implicitly_wait(5)
    if not HEADLESS:
        logging.info(f"➜ Chrome (worker {stamp}) headless={HEADLESS}")
    return driver

def is_page_maintenance(driver):
    body = driver.find_element(By.TAG_NAME, "body").text.lower()
    return any(k in body for k in ("mantenimiento","temporalmente fuera"))
