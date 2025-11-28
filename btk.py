import time
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from browser import get_driver
from captcha.manager import CaptchaManager
from config import CAPTCHA_PROVIDERS
from utils import logger, SorguSonucu
from PIL import Image, ImageOps

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
            img = ImageOps.expand(img, border=20, fill='white')
            base, ext = os.path.splitext(image_path)
            processed_path = f"{base}_proc{ext}"
            img.save(processed_path)
            return processed_path
        except:
            return image_path

    def _tek_sorgu(self, domain: str) -> SorguSonucu:
        """Tek bir tarama işlemini gerçekleştirir."""
        driver = None
        start_time = time.time()
        img_path = f"temp_captcha_{domain}.png"
        screenshots = [] 
        
        try:
            driver = get_driver()
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
            
            time.sleep(0.5)
            btn_sorgula.click()
            time.sleep(3.0) 
            
            page_source = driver.page_source.lower()
            durum = "BİLİNMİYOR"
            detay = "Analiz edilemedi"

            if "yanlış girdiniz" in page_source or "hatalı" in page_source:
                durum = "HATA"
                detay = "Captcha veya Veri Hatası"
            elif "engellenmiştir" in page_source:
                durum = "ENGELLİ"
                # --- KOORDİNATLARA GÖRE KIRPMA ---
                try:
                    full_path = f"full_temp_{domain}.png"
                    driver.save_screenshot(full_path)
                    with Image.open(full_path) as img:
                        # Koordinatlar: (Sol, Üst, Sağ, Alt)
                        crop_area = (472, 0, 1433, 597)
                        cropped_img = img.crop(crop_area)
                        
                        s3 = f"kanit_{domain}.png"
                        cropped_img.save(s3)
                        screenshots.append(s3)
                    if os.path.exists(full_path): os.remove(full_path)
                except Exception as e:
                     logger.warning(f"Kırpma hatası: {e}")
                     # Hata olursa tam sayfa al
                     s3_full = f"full_kanit_{domain}.png"
                     driver.save_screenshot(s3_full)
                     screenshots.append(s3_full)
                # ---------------------------------
            elif "bulunamadı" in page_source:
                durum = "TEMİZ"
            
            total_time = round(time.time() - start_time, 2)
            return SorguSonucu(domain, durum, detay, total_time, captcha_code, screenshot_paths=screenshots)

        except Exception as e:
            return SorguSonucu(domain, "HATA", str(e), 0.0, screenshot_paths=screenshots)
        finally:
            if driver: driver.quit()
            if os.path.exists(img_path):
                try: os.remove(img_path) 
                except: pass
            if 'final_captcha_path' in locals() and os.path.exists(final_captcha_path):
                try: os.remove(final_captcha_path)
                except: pass

    # DÜZELTME: Deneme sayısı 10'a çıkarıldı
    def sorgula(self, domain: str, max_retries=10) -> SorguSonucu:
        """
        Hata durumunda belirtilen sayı kadar tekrar dener.
        """
        sonuc = None
        for attempt in range(1, max_retries + 1):
            if attempt > 1:
                logger.info(f"🔄 {domain} tekrar deneniyor ({attempt}/{max_retries})...")
            
            sonuc = self._tek_sorgu(domain)
            
            # Eğer durum HATA değilse (TEMİZ veya ENGELLİ ise) sonucu hemen döndür
            if sonuc.durum != "HATA":
                return sonuc
            
            # Hata aldıysak biraz bekle ve tekrar dene
            time.sleep(2)
        
        # Deneme hakkı bitti, son alınan sonucu (HATA) döndür
        return sonuc
