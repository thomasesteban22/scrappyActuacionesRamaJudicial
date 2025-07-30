import os, time, logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from .config import HEADLESS, CHROME_BIN, CHROMEDRIVER_PATH

# Silencia logs de webdriver_manager
logging.getLogger('WDM').setLevel(logging.ERROR)
logging.getLogger('webdriver_manager').setLevel(logging.ERROR)

def new_chrome_driver(worker_id=None):
    opts = webdriver.ChromeOptions()
    opts.add_argument("--remote-allow-origins=*")
    opts.add_experimental_option("excludeSwitches", ["enable-automation","enable-logging"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--disable-blink-features=AutomationControlled")
    # bloquear solo imágenes
    prefs = {"profile.managed_default_content_settings.images": 2}
    opts.add_experimental_option("prefs", prefs)
    opts.add_argument("--log-level=3")

    if HEADLESS:
        opts.add_argument("--headless")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1920,1080")
    else:
        opts.add_argument("--start-maximized")

    # perfil aislado
    base = os.path.join(os.getcwd(), "tmp_profiles")
    os.makedirs(base, exist_ok=True)
    stamp = worker_id or int(time.time()*1000)
    profile_dir = os.path.join(base, f"profile_{stamp}")
    os.makedirs(profile_dir, exist_ok=True)
    opts.add_argument(f"--user-data-dir={profile_dir}")

    # binario Chrome
    if CHROME_BIN and os.path.isfile(CHROME_BIN):
        opts.binary_location = CHROME_BIN

    # chromedriver
    if CHROMEDRIVER_PATH and os.path.isfile(CHROMEDRIVER_PATH):
        svc = Service(executable_path=CHROMEDRIVER_PATH, log_path=os.devnull)
    else:
        from webdriver_manager.chrome import ChromeDriverManager
        drv = ChromeDriverManager().install()
        svc = Service(executable_path=drv, log_path=os.devnull)

    driver = webdriver.Chrome(service=svc, options=opts)
    driver.set_page_load_timeout(60)
    driver.implicitly_wait(10)
    return driver
