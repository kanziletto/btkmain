import time
import os  # ✅ BU SATIR KRİTİK
import io
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from browser import get_driver
from captcha.manager import CaptchaManager
from config import CAPTCHA_PROVIDERS
from utils import logger, SorguSonucu
from PIL import Image

class BTKScanner:
    def __init__(self):
        self.base_url = "https://internet2.btk.gov.tr/sitesorgu/"
        self.captcha_mgr = CaptchaManager(CAPTCHA_PROVIDERS)

    def preprocess_image(self, image_path: str) -> str:
        try:
            img = Image.open(image_path)
            w, h = img.size
            img = img.crop((2, 2, w - 2, h - 2))
            img = img.resize((w * 2, h * 2), Image.Resampling.LANCZOS)
            base, ext = os.path.splitext(image_path)
            processed_path = f"{base}_proc{ext}"
            img.save(processed_path)
            return processed_path
        except:
            return image_path

    def _take_screenshot(self, driver, domain):
        """Yardımcı Fonksiyon: Ekran görüntüsü alır"""
        try:
            full_path = f"full_temp_{domain}.png"
            driver.save_screenshot(full_path)
            try:
                # Kırpma denemesi
                with Image.open(full_path) as img:
                    crop_area = (472, 0, 1433, 597)
                    cropped_img = img.crop(crop_area)
                    # RAM (BytesIO) olarak döndürelim ki disk yorulmasın
                    output = io.BytesIO()
                    cropped_img.save(output, format='PNG')
                    output.seek(0)
                    return output
            except:
                # Kırpamazsa dosyayı oku ve döndür
                with open(full_path, 'rb') as f:
                    return io.BytesIO(f.read())
            finally:
                # Temizlik
                if os.path.exists(full_path):
                    try: os.remove(full_path)
                    except: pass
        except Exception as e:
            logger.warning(f"Screenshot hatası: {e}")
            return None

    def _tek_sorgu(self, domain: str, force_screenshot=False) -> SorguSonucu:
        start_time = time.time()
        img_path = f"temp_captcha_{domain}.png"
        final_captcha_path = None
        screenshots = [] 
        
        try:
            with get_driver() as driver:
                driver.get(self.base_url)
                wait = WebDriverWait(driver, 30)

                input_domain = wait.until(EC.visibility_of_element_located((By.ID, "deger")))
                input_captcha = driver.find_element(By.ID, "security_code")
                captcha_img = wait.until(EC.visibility_of_element_located((By.ID, "security_code_image")))
                btn_sorgula = driver.find_element(By.ID, "submit1")

                captcha_img.screenshot(img_path)
                final_captcha_path = self.preprocess_image(img_path)
                captcha_code, provider = self.captcha_mgr.solve(final_captcha_path)
                
                input_domain.clear()
                input_domain.send_keys(domain)
                input_captcha.clear()
                input_captcha.send_keys(captcha_code)
                
                time.sleep(0.1)
                btn_sorgula.click()
                
                # Akıllı Bekleme
                try:
                    wait.until(lambda d: any(x in d.page_source.lower() for x in ["engellenmiştir", "bulunamadı", "yanlış", "hatalı"]))
                except: pass
                
                page_source = driver.page_source.lower()
                durum = "BİLİNMİYOR"
                detay = "Analiz edilemedi"

                if "yanlış girdiniz" in page_source or "hatalı" in page_source:
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
            logger.error(f"Tarama hatası ({domain}): {e}")
            return SorguSonucu(domain, "HATA", str(e), 0.0, screenshot_paths=screenshots)
        
        finally:
            # Temizlik işlemleri (os modülü burada kullanılıyor)
            if os.path.exists(img_path):
                try: os.remove(img_path) 
                except: pass
            if final_captcha_path and os.path.exists(final_captcha_path):
                try: os.remove(final_captcha_path)
                except: pass

    def sorgula(self, domain: str, max_retries=10, force_screenshot=False) -> SorguSonucu:
        sonuc = None
        for attempt in range(1, max_retries + 1):
            if attempt > 1:
                logger.info(f"🔄 {domain} tekrar deneniyor ({attempt}/{max_retries})...")
            
            sonuc = self._tek_sorgu(domain, force_screenshot=force_screenshot)
            
            if sonuc.durum != "HATA":
                return sonuc
            
            time.sleep(1)
        
        logger.error(f"❌ {domain}: {max_retries} denemede başarısız oldu")
        return sonuc
