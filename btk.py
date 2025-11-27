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
        """
        SADECE BÜYÜTME:
        Ağır işlem yok. Resmi 2 kat büyütüp API'ye yollar.
        """
        try:
            img = Image.open(image_path)
            
            # Kenar temizliği (Çerçeveyi at)
            w, h = img.size
            img = img.crop((2, 2, w - 2, h - 2))
            
            # Büyütme (Upscale x2)
            img = img.resize((w * 2, h * 2), Image.Resampling.LANCZOS)
            
            # Çerçeve Ekle
            img = ImageOps.expand(img, border=20, fill='white')

            base, ext = os.path.splitext(image_path)
            processed_path = f"{base}_proc{ext}"
            img.save(processed_path)
            return processed_path
        except:
            return image_path

    def sorgula(self, domain: str) -> SorguSonucu:
        # (Standart sorgu fonksiyonu)
        driver = None
        start_time = time.time()
        img_path = f"temp_captcha_{domain}.png"
        screenshots = [] 
        
        try:
            logger.info(f"🚀 {domain} için DEBUG testi başlıyor...")
            driver = get_driver()
            driver.get(self.base_url)
            wait = WebDriverWait(driver, 30)

            input_domain = wait.until(EC.visibility_of_element_located((By.ID, "deger")))
            input_captcha = driver.find_element(By.ID, "security_code")
            captcha_img = wait.until(EC.visibility_of_element_located((By.ID, "security_code_image")))
            btn_sorgula = driver.find_element(By.ID, "submit1")

            s1 = f"debug1_orj_{domain}.png"
            driver.save_screenshot(s1)
            screenshots.append(s1)

            captcha_img.screenshot(img_path)
            
            # İŞLEME
            final_captcha_path = self.preprocess_image(img_path)
            screenshots.append(final_captcha_path)

            # ÇÖZME (Remote API)
            captcha_code, provider = self.captcha_mgr.solve(final_captcha_path)
            
            logger.info(f"🧩 Captcha: {captcha_code} ({provider})")

            input_domain.clear()
            input_domain.send_keys(domain)
            input_captcha.clear()
            input_captcha.send_keys(captcha_code)
            
            s2 = f"debug2_yazilan_{domain}.png"
            driver.save_screenshot(s2)
            screenshots.append(s2)

            time.sleep(0.5)
            btn_sorgula.click()
            time.sleep(3.0) 
            
            s3 = f"debug3_sonuc_{domain}.png"
            driver.save_screenshot(s3)
            screenshots.append(s3)

            page_source = driver.page_source.lower()
            durum = "BİLİNMİYOR"
            detay = "Analiz edilemedi"

            if "yanlış girdiniz" in page_source or "hatalı" in page_source:
                durum = "HATA"
            elif "engellenmiştir" in page_source:
                durum = "ENGELLİ"
            elif "bulunamadı" in page_source:
                durum = "TEMİZ"
            
            total_time = round(time.time() - start_time, 2)
            return SorguSonucu(domain, durum, detay, total_time, captcha_code, screenshot_paths=screenshots)

        except Exception as e:
            logger.error(f"❌ Hata: {str(e)}")
            return SorguSonucu(domain, "KRİTİK HATA", str(e), 0.0, screenshot_paths=screenshots)
        finally:
            if driver: driver.quit()
