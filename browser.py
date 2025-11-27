from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from config import HEADLESS_MODE, get_random_proxy
from utils import logger

def get_driver():
    options = webdriver.ChromeOptions()
    
    if HEADLESS_MODE:
        options.add_argument("--headless=new")
    
    # --- CRASH ÖNLEYİCİ AYARLAR ---
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")                 # Ekran kartı yok, kapat
    options.add_argument("--disable-software-rasterizer") # Yazılımsal render'ı kapat
    options.add_argument("--disable-extensions")          # Eklentileri kapat
    options.add_argument("--remote-debugging-port=9222")  # Hata ayıklama portu (Çökmemesi için gerekli olabiliyor)
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")
    
    # Anti-Tespit
    options.add_argument("--disable-blink-features=AutomationControlled") 
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Proxy
    proxy = get_random_proxy()
    if proxy:
        options.add_argument(f'--proxy-server={proxy}')

    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")

    try:
        # Selenium Driver Manager (Otomatik)
        driver = webdriver.Chrome(service=Service(), options=options)
        return driver
    except Exception as e:
        logger.error(f"Driver başlatılamadı: {e}")
        raise e
