from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from config import HEADLESS_MODE, get_random_proxy
from utils import logger
import queue
import atexit

# Global driver havuzu
_driver_pool = None
_pool_size = 2

def _create_driver():
    """Yeni bir driver oluşturur (dahili kullanım)"""
    options = webdriver.ChromeOptions()
    
    if HEADLESS_MODE:
        options.add_argument("--headless=new")
    
    # --- CRASH ÖNLEYİCİ AYARLAR ---
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
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
        driver = webdriver.Chrome(service=Service(), options=options)
        logger.info(f"✅ Yeni Chrome başlatıldı")
        return driver
    except Exception as e:
        logger.error(f"Driver başlatılamadı: {e}")
        raise e

def init_driver_pool():
    """Driver havuzunu başlatır (uygulama başlangıcında bir kez çağrılır)"""
    global _driver_pool
    
    if _driver_pool is not None:
        logger.warning("⚠️ Driver havuzu zaten başlatılmış!")
        return  # Zaten başlatılmış
    
    logger.info(f"🔧 {_pool_size} adet Chrome başlatılıyor...")
    _driver_pool = queue.Queue(maxsize=_pool_size)
    
    for i in range(_pool_size):
        try:
            driver = _create_driver()
            _driver_pool.put(driver)
            logger.info(f"✅ Chrome #{i+1} havuza eklendi")
        except Exception as e:
            logger.error(f"❌ Chrome #{i+1} başlatılamadı: {e}")
            # İlk Chrome bile başlamazsa hata fırlat
            if i == 0:
                raise Exception("Hiçbir Chrome başlatılamadı!")
    
    # Uygulama kapatıldığında temizlik yap
    atexit.register(cleanup_driver_pool)
    logger.info(f"🎉 Driver havuzu hazır! ({_pool_size} Chrome)")

def cleanup_driver_pool():
    """Tüm driver'ları kapat (uygulama kapanışında otomatik çağrılır)"""
    global _driver_pool
    
    if _driver_pool is None:
        return
    
    logger.info("🧹 Driver havuzu temizleniyor...")
    closed_count = 0
    
    while not _driver_pool.empty():
        try:
            driver = _driver_pool.get_nowait()
            driver.quit()
            closed_count += 1
        except Exception as e:
            logger.warning(f"⚠️ Driver kapatma hatası: {e}")
    
    _driver_pool = None
    logger.info(f"✅ {closed_count} Chrome kapatıldı")

def get_driver():
    """
    Havuzdan bir driver al (context manager ile kullanılır)
    
    Kullanım:
        with get_driver() as driver:
            driver.get("https://example.com")
            # ... işlemler
        # Blok bitince otomatik havuza geri koyulur
    """
    if _driver_pool is None:
        logger.warning("⚠️ Driver havuzu başlatılmamış, şimdi başlatılıyor...")
        init_driver_pool()
    
    class DriverContext:
        def __enter__(self):
            """Blok başladığında havuzdan driver al"""
            self.driver = _driver_pool.get()  # Havuzdan al (havuz boşsa bekler)
            logger.debug(f"🔵 Driver havuzdan alındı (Kalan: {_driver_pool.qsize()})")
            return self.driver
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            """Blok bittiğinde driver'ı temizle ve havuza geri koy"""
            
            if exc_type is not None:
                # Hata oluştuysa driver'ı yenile
                logger.warning(f"⚠️ Driver hatası: {exc_val}")
                logger.info("🔄 Bozuk driver yenileniyor...")
                try:
                    self.driver.quit()  # Eski Chrome'u kapat
                except Exception as e:
                    logger.error(f"❌ Driver kapatma hatası: {e}")
                
                try:
                    self.driver = _create_driver()  # Yeni Chrome oluştur
                    logger.info("✅ Yeni driver oluşturuldu")
                except Exception as e:
                    logger.error(f"❌ Yeni driver oluşturulamadı: {e}")
                    # Yeni driver oluşturulamazsa boş havuza dönme
                    return False
            else:
                # Başarılıysa sayfayı temizle
                try:
                    self.driver.delete_all_cookies()
                    self.driver.execute_script("window.localStorage.clear();")
                    self.driver.execute_script("window.sessionStorage.clear();")
                except Exception as e:
                    logger.warning(f"⚠️ Temizlik hatası (önemsiz): {e}")
            
            # Havuza geri koy
            _driver_pool.put(self.driver)
            logger.debug(f"🟢 Driver havuza geri kondu (Toplam: {_driver_pool.qsize()})")
            
            # Hatayı yutma (False döndürürse hata yutar)
            return False
    
    return DriverContext()
