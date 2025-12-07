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

class BTKScanner:
    def __init__(self):
        self.base_url = "https://internet2.btk.gov.tr/sitesorgu/"
        self.captcha_mgr = CaptchaManager(CAPTCHA_PROVIDERS)
        self._page_loaded = False  # Sayfa yüklü mü?

    def preprocess_captcha(self, png_data: bytes) -> bytes:
        """
        Captcha görselini ön işlemden geçirir - OCR başarısını artırır.
        Giriş: PNG bytes
        Çıkış: İşlenmiş PNG bytes
        """
        try:
            from PIL import ImageOps, ImageFilter
            
            img = Image.open(io.BytesIO(png_data))
            w, h = img.size
            
            # 1. Kenar kırpma (gürültü azaltma)
            img = img.crop((2, 2, w - 2, h - 2))
            
            # 2. Büyütme (3x) - OCR için daha net görüntü
            new_w, new_h = img.size
            img = img.resize((new_w * 3, new_h * 3), Image.Resampling.LANCZOS)
            
            # 3. Gri tonlamaya çevir
            img = img.convert('L')
            
            # 4. Otomatik kontrast - histogram germe
            img = ImageOps.autocontrast(img, cutoff=5)
            
            # 5. Gürültü azaltma - median filtre
            img = img.filter(ImageFilter.MedianFilter(size=3))
            
            # 6. Dinamik threshold (ortalama tabanlı)
            pixels = list(img.getdata())
            avg_pixel = sum(pixels) / len(pixels)
            threshold = int(avg_pixel * 0.85)  # Ortalamanın biraz altı
            img = img.point(lambda x: 0 if x < threshold else 255, '1')
            
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

    def _tek_sorgu(self, domain: str, driver, force_screenshot=False) -> SorguSonucu:
        """Tek bir sorgu yapar - driver dışarıdan verilir"""
        start_time = time.time()
        screenshots = [] 
        
        try:
            # Polling interval: 0.2s (varsayılan 0.5s'den hızlı)
            wait = WebDriverWait(driver, 15, poll_frequency=0.2)
            
            # Sayfa yüklü değilse veya elementler bulunamıyorsa yeniden yükle
            try:
                input_domain = driver.find_element(By.ID, "deger")
                input_captcha = driver.find_element(By.ID, "security_code")
                captcha_img = driver.find_element(By.ID, "security_code_image")
                btn_sorgula = driver.find_element(By.ID, "submit1")
                
                # Elementler stale mi kontrol et
                input_domain.is_displayed()
            except (StaleElementReferenceException, Exception):
                # Sayfa yeniden yüklenmeli
                driver.get(self.base_url)
                input_domain = wait.until(EC.visibility_of_element_located((By.ID, "deger")))
                input_captcha = driver.find_element(By.ID, "security_code")
                captcha_img = wait.until(EC.visibility_of_element_located((By.ID, "security_code_image")))
                btn_sorgula = driver.find_element(By.ID, "submit1")

            # Captcha al, ön işle ve çöz
            png_data = captcha_img.screenshot_as_png
            processed_png = self.preprocess_captcha(png_data)
            captcha_code, provider = self.captcha_mgr.solve(processed_png)
            
            # Form doldur
            input_domain.clear()
            input_domain.send_keys(domain)
            input_captcha.clear()
            input_captcha.send_keys(captcha_code)
            
            btn_sorgula.click()
            
            # Akıllı Bekleme (hızlandırılmış polling)
            try:
                wait.until(lambda d: any(x in d.page_source.lower() for x in ["engellenmiştir", "bulunamadı", "yanlış", "hatalı"]))
            except TimeoutException:
                pass
            
            page_source = driver.page_source.lower()
            durum = "BİLİNMİYOR"
            detay = "Analiz edilemedi"

            if "yanlış girdiniz" in page_source or "hatalı" in page_source:
                durum = "HATA"
                detay = "Captcha/Veri Hatası"
                # Captcha yanlış girildiyse sayfayı yenile (yeni captcha için)
                driver.get(self.base_url)
            
            elif "engellenmiştir" in page_source:
                durum = "ENGELLİ"
                ss = self._take_screenshot(driver, domain)
                if ss: screenshots.append(ss)
                # Sayfa yenileme YOK - sonraki sorguda element kontrolü yapılacak
            
            elif "bulunamadı" in page_source:
                durum = "TEMİZ"
                if force_screenshot:
                    ss = self._take_screenshot(driver, domain)
                    if ss: screenshots.append(ss)
                # Sayfa yenileme YOK - sonraki sorguda element kontrolü yapılacak
            
            total_time = round(time.time() - start_time, 2)
            return SorguSonucu(domain, durum, detay, total_time, captcha_code, screenshot_paths=screenshots)

        except Exception as e:
            logger.error(f"Tarama hatası ({domain}): {e}")
            # Hata durumunda sayfayı yeniden yükle
            try:
                driver.get(self.base_url)
            except:
                pass
            return SorguSonucu(domain, "HATA", str(e), 0.0, screenshot_paths=screenshots)

    def sorgula(self, domain: str, max_retries=5, force_screenshot=False) -> SorguSonucu:
        """Domain sorgular - driver havuzdan alınır ve yeniden kullanılır"""
        sonuc = None
        
        with get_driver() as driver:
            # İlk açılışta sayfayı yükle
            try:
                driver.get(self.base_url)
            except:
                pass
            
            for attempt in range(1, max_retries + 1):
                if attempt > 1:
                    logger.info(f"🔄 {domain} tekrar deneniyor ({attempt}/{max_retries})...")
                
                sonuc = self._tek_sorgu(domain, driver, force_screenshot=force_screenshot)
                
                if sonuc.durum != "HATA":
                    # Başarılı - kaç denemede olduğunu logla
                    if attempt > 1:
                        logger.info(f"✅ {domain} {attempt}. denemede başarılı")
                    return sonuc
                
                # Retry öncesi biraz daha bekle (captcha yenilensin)
                time.sleep(1.0)
            
            logger.error(f"❌ {domain}: {max_retries} denemede başarısız oldu")
            return sonuc
