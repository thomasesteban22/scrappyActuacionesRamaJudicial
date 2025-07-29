import os, time, logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from .config import HEADLESS, CHROME_BIN, CHROMEDRIVER_PATH

# Silencia logs internos
for log in ("WDM", "webdriver_manager", "absl"):
    logging.getLogger(log).setLevel(logging.ERROR)

def new_chrome_driver(worker_id=None):
    opts = webdriver.ChromeOptions()
    # 1) Desktop UA + tamaño
    opts.add_argument("--remote-allow-origins=*")
    opts.add_experimental_option("excludeSwitches", ["enable-automation","enable-logging"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.7204.168 Safari/537.36"
    )

    # 2) Bloqueo recursos
    prefs = {
        "profile.managed_default_content_settings.images":      2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.fonts":       2,
    }
    opts.add_experimental_option("prefs", prefs)
    opts.add_argument("--log-level=3")

    # 3) Headless?
    if HEADLESS:
        opts.add_argument("--headless")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
    else:
        opts.add_argument("--start-maximized")

    # 4) Perfil aislado
    base = os.path.join(os.getcwd(), "tmp_profiles")
    os.makedirs(base, exist_ok=True)
    stamp = worker_id or int(time.time()*1000)
    profile = os.path.join(base, f"profile_{stamp}")
    os.makedirs(profile, exist_ok=True)
    opts.add_argument(f"--user-data-dir={profile}")

    # 5) Binarios
    if CHROME_BIN and os.path.isfile(CHROME_BIN):
        opts.binary_location = CHROME_BIN
    svc = Service(executable_path=CHROMEDRIVER_PATH, log_path=os.devnull)

    # 6) Eager (no espera imágenes/CSS)
    opts.page_load_strategy = "eager"

    # 7) Arranque silencioso
    _out, _err = os.dup(1), os.dup(2)
    devnull = os.open(os.devnull, os.O_RDWR)
    try:
        os.dup2(devnull, 1); os.dup2(devnull, 2)
        driver = webdriver.Chrome(service=svc, options=opts)
    finally:
        os.dup2(_out,1); os.dup2(_err,2)
        os.close(_out); os.close(_err); os.close(devnull)

    driver.set_page_load_timeout(120)
    driver.implicitly_wait(5)
    return driver
