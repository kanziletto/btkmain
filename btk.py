import time
import os
import io
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from browser import get_driver
from captcha.manager import CaptchaManager
from config import CAPTCHA_PROVIDERS
from utils import logger, SorguSonucu
from PIL import Image

class CriticalDriverError(Exception):
    def __init__(self, message, screenshot=None):
        super().__init__(message)
        self.screenshot = screenshot

class BTKScanner:
    def __init__(self):
        self.base_url = "https://internet2.btk.gov.tr/sitesorgu/"
        self.captcha_mgr = CaptchaManager(CAPTCHA_PROVIDERS)

    def preprocess_captcha(self, png_data: bytes) -> bytes:
        """
        Captcha görselini ön işlemden geçirir - 2x büyütme (GitHub gibi)
        """
        try:
            img = Image.open(io.BytesIO(png_data))
            w, h = img.size
            
            # 1. Kenar kırpma (gürültü azaltma)
            img = img.crop((2, 2, w - 2, h - 2))
            
            # 2. 2x büyütme (GitHub versiyonu gibi)
            new_w, new_h = img.size
            img = img.resize((new_w * 2, new_h * 2), Image.Resampling.LANCZOS)
            
            # BytesIO olarak döndür
            output = io.BytesIO()
            img.save(output, format='PNG')
            output.seek(0)
            return output.read()
        except Exception as e:
            logger.warning(f"Captcha ön işleme hatası: {e}")
            return png_data

    def _take_screenshot(self, driver, domain):
        """Yardımcı Fonksiyon: Ekran görüntüsü alır"""
        try:
            full_path = f"full_temp_{domain}.png"
            driver.save_screenshot(full_path)
            try:
                # Kırpma denemesi
                with Image.open(full_path) as img:
                    crop_area = (448, 0, 1458, 555)
                    cropped_img = img.crop(crop_area)
                    # RAM (BytesIO) olarak döndürelim
                    output = io.BytesIO()
                    cropped_img.save(output, format='PNG')
                    output.seek(0)
                    return output
            except:
                with open(full_path, 'rb') as f:
                    return io.BytesIO(f.read())
            finally:
                if os.path.exists(full_path):
                    try: os.remove(full_path)
                    except: pass
        except Exception as e:
            logger.warning(f"Screenshot hatası: {e}")
            return None

    def _tek_sorgu(self, domain: str, driver, force_screenshot=False) -> SorguSonucu:
        """Tek bir sorgu yapar - HER SEFERINDE SAYFA YENİLENİR (GitHub gibi)"""
        start_time = time.time()
        screenshots = [] 
        
        try:
            wait = WebDriverWait(driver, 30, poll_frequency=0.2)
            
            # HER SORGUDA SAYFA YENİLE (GitHub versiyonu gibi)
            driver.get(self.base_url)
            
            input_domain = wait.until(EC.visibility_of_element_located((By.ID, "deger")))
            input_captcha = wait.until(EC.visibility_of_element_located((By.ID, "security_code")))
            captcha_img = wait.until(EC.visibility_of_element_located((By.ID, "security_code_image")))
            btn_sorgula = wait.until(EC.element_to_be_clickable((By.ID, "submit1")))

            # Captcha al, 2x büyüt ve çöz (RAM'de)
            png_data = captcha_img.screenshot_as_png
            processed_png = self.preprocess_captcha(png_data)
            captcha_code, provider = self.captcha_mgr.solve(processed_png)
            
            # Form doldur
            input_domain.clear()
            input_domain.send_keys(domain)
            input_captcha.clear()
            input_captcha.send_keys(captcha_code)
            
            btn_sorgula.click()
            
            # Akıllı Bekleme
            try:
                wait.until(lambda d: any(x in d.page_source.lower() for x in ["engellenmiştir", "bulunamadı", "yanlış", "hatalı"]))
            except TimeoutException:
                pass
            
            page_source = driver.page_source.lower()
            durum = "BİLİNMİYOR"
            detay = "Analiz edilemedi"
            
            # DEBUG: Captcha ve sonuç logla
            logger.info(f"🔍 {domain} | Captcha: '{captcha_code}' | Sonuç bekleniyor...")

            if "yanlış girdiniz" in page_source or "hatalı" in page_source:
                logger.warning(f"❌ {domain} | Captcha YANLIŞ: '{captcha_code}'")
                durum = "HATA"
                detay = "Captcha/Veri Hatası"
            
            elif "engellenmiştir" in page_source:
                durum = "ENGELLİ"
                ss = self._take_screenshot(driver, domain)
                if ss: screenshots.append(ss)
            
            elif "bulunamadı" in page_source:
                durum = "TEMİZ"
                if force_screenshot:
                    ss = self._take_screenshot(driver, domain)
                    if ss: screenshots.append(ss)
            
            total_time = round(time.time() - start_time, 2)
            return SorguSonucu(domain, durum, detay, total_time, captcha_code, screenshot_paths=screenshots)

        except Exception as e:
            # Hata durumunda da SS almayı dene
            try:
                ss = self._take_screenshot(driver, domain)
                if ss: screenshots.append(ss)
            except: pass

            # KRİTİK HATALARI YAKALAYIP FIRLAT (Driver yenilensin diye)
            msg = str(e).lower()
            if "renderer" in msg or "timeout" in msg or "disconnected" in msg or "closed" in msg:
                # Screenshot'ı exception ile yukarı taşı
                raise CriticalDriverError(str(e), screenshot=screenshots[0] if screenshots else None)
            
            logger.error(f"Tarama hatası ({domain}): {e}")
            return SorguSonucu(domain, "HATA", str(e), 0.0, screenshot_paths=screenshots)

    def sorgula(self, domain: str, max_retries=10, force_screenshot=False) -> SorguSonucu:
        """Domain sorgular - HER DENEMEDE driver havuzdan alınır (Robust)"""
        sonuc = None
        
        for attempt in range(1, max_retries + 1):
            try:
                # Driver'ı döngü İÇİNDE alıyoruz ki hata durumunda yenilensin
                with get_driver() as driver:
                    if attempt > 1:
                        logger.info(f"🔄 {domain} tekrar deneniyor ({attempt}/{max_retries})...")
                    
                    sonuc = self._tek_sorgu(domain, driver, force_screenshot=force_screenshot)
                    
                    if sonuc.durum != "HATA":
                        if attempt > 1:
                            logger.info(f"✅ {domain} {attempt}. denemede başarılı")
                        return sonuc
            
            except CriticalDriverError as e:
                # Kritik hata: Driver öldü, ama elimizde SS olabilir
                logger.warning(f"⚠️ Driver CRITICAL ({domain}): {e}... Driver yenileniyor.")
                
                # Sonucu kaydet (son deneme ise bunu döndüreceğiz)
                sonuc = SorguSonucu(domain, "HATA", f"Critical: {e}", 0.0, screenshot_paths=[e.screenshot] if e.screenshot else [])
                time.sleep(2)
                continue

            except Exception as e:
                # Driver crash/timeout durumunda buraya düşer (Context manager driver'ı discard etti)
                logger.warning(f"⚠️ Driver crash/timeout ({domain}): {e}... Yeni driver bekleniyor.")
                time.sleep(2)
                continue
            
            # Normal hata (kaptcha yanlış vs) - biraz bekle ve tekrar dene
            time.sleep(1)
        
        logger.error(f"❌ {domain}: {max_retries} denemede başarısız oldu")
        return sonuc if sonuc else SorguSonucu(domain, "HATA", "Max retries exceeded", 0.0)

