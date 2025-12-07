"""
RapidOCR Test Script - Mevcut Bot Altyapısını Kullanır
Bu script captcha çözme başarı oranını test eder.
"""
import time
import os
import sys

# Bot modüllerini import et
from browser import init_driver_pool, get_driver, cleanup_driver_pool
from captcha.manager import CaptchaManager
from config import CAPTCHA_PROVIDERS, OCR_API_URL
from PIL import Image
import io
import requests

# --- AYARLAR ---
BTK_URL = "https://internet2.btk.gov.tr/sitesorgu/"
TEST_DOMAIN = "google.com"  # Bilinen temiz domain
NUM_TESTS = 10  # Kaç test yapılacak

def preprocess_captcha(png_data: bytes) -> bytes:
    """Captcha görselini ön işlemden geçir - OCR başarısını artırır"""
    try:
        img = Image.open(io.BytesIO(png_data))
        w, h = img.size
        
        # 1. Kenar kırpma (gürültü azaltma)
        img = img.crop((2, 2, w - 2, h - 2))
        
        # 2. Büyütme (2x) - OCR için daha net
        new_w, new_h = img.size
        img = img.resize((new_w * 2, new_h * 2), Image.Resampling.LANCZOS)
        
        # 3. Gri tonlamaya çevir
        img = img.convert('L')
        
        # 4. Kontrast artırma (threshold)
        img = img.point(lambda x: 0 if x < 140 else 255, '1')
        
        # BytesIO olarak döndür
        output = io.BytesIO()
        img.save(output, format='PNG')
        output.seek(0)
        return output.read()
    except Exception as e:
        print(f"Ön işleme hatası: {e}")
        return png_data

def single_test(driver, captcha_mgr, test_num: int, use_preprocess: bool = True) -> dict:
    """Tek bir test çalıştır"""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    start = time.time()
    
    try:
        driver.get(BTK_URL)
        wait = WebDriverWait(driver, 15)
        
        # Elementleri bul
        input_domain = wait.until(EC.visibility_of_element_located((By.ID, "deger")))
        input_captcha = driver.find_element(By.ID, "security_code")
        captcha_img = wait.until(EC.visibility_of_element_located((By.ID, "security_code_image")))
        btn_submit = driver.find_element(By.ID, "submit1")
        
        # Captcha al
        png_data = captcha_img.screenshot_as_png
        
        # Captcha'yı kaydet (debug için)
        debug_dir = "captcha_debug"
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
        
        with open(f"{debug_dir}/captcha_{test_num}.png", 'wb') as f:
            f.write(png_data)
        
        # Ön işleme
        if use_preprocess:
            processed_png = preprocess_captcha(png_data)
            with open(f"{debug_dir}/captcha_{test_num}_processed.png", 'wb') as f:
                f.write(processed_png)
        else:
            processed_png = png_data
        
        # OCR çöz (mevcut CaptchaManager kullan)
        captcha_text, provider = captcha_mgr.solve(processed_png)
        print(f"  [Test {test_num}] OCR: '{captcha_text}' ({provider})", end=" ")
        
        if not captcha_text or len(captcha_text) < 3 or captcha_text == "00000":
            print("❌ OCR boş/başarısız")
            return {"status": "ocr_fail", "time": time.time() - start}
        
        # Form doldur ve gönder
        input_domain.clear()
        input_domain.send_keys(TEST_DOMAIN)
        input_captcha.clear()
        input_captcha.send_keys(captcha_text)
        btn_submit.click()
        
        # Sonucu bekle
        time.sleep(2)
        page_source = driver.page_source.lower()
        
        if "yanlış girdiniz" in page_source or "hatalı" in page_source:
            print("❌ Captcha yanlış")
            # Başarısız captcha'yı ayrı kaydet
            with open(f"{debug_dir}/FAIL_{test_num}_{captcha_text}.png", 'wb') as f:
                f.write(png_data)
            return {"status": "captcha_error", "time": time.time() - start, "ocr_text": captcha_text}
        
        elif "bulunamadı" in page_source or "engellenmiştir" in page_source:
            print("✅ Başarılı!")
            return {"status": "success", "time": time.time() - start, "ocr_text": captcha_text}
        
        else:
            print("⚠️ Bilinmeyen sonuç")
            return {"status": "unknown", "time": time.time() - start}
            
    except Exception as e:
        print(f"❌ Hata: {e}")
        return {"status": "error", "time": time.time() - start, "error": str(e)}

def main():
    print("=" * 60)
    print("🧪 RapidOCR Captcha Test (Bot Altyapısı)")
    print("=" * 60)
    print(f"OCR API: {OCR_API_URL}")
    print(f"Test Sayısı: {NUM_TESTS}")
    print(f"Test Domain: {TEST_DOMAIN}")
    print("-" * 60)
    
    # API bağlantı testi
    print("\n📡 OCR API bağlantı testi...")
    try:
        test_img = Image.new('RGB', (100, 40), color='white')
        img_bytes = io.BytesIO()
        test_img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        response = requests.post(OCR_API_URL, files={'file': ('test.png', img_bytes, 'image/png')}, timeout=5)
        if response.status_code == 200:
            print("✅ OCR API erişilebilir!")
        else:
            print(f"❌ OCR API hata: HTTP {response.status_code}")
            return
    except Exception as e:
        print(f"❌ OCR API bağlantı hatası: {e}")
        return
    
    # CaptchaManager başlat
    captcha_mgr = CaptchaManager(CAPTCHA_PROVIDERS)
    
    # Driver havuzunu başlat
    print("\n🔧 Chrome başlatılıyor...")
    try:
        init_driver_pool()
    except Exception as e:
        print(f"❌ Chrome başlatılamadı: {e}")
        return
    
    try:
        print("\n🔄 Testler başlıyor...\n")
        
        success_count = 0
        captcha_fail_count = 0
        ocr_fail_count = 0
        other_fail_count = 0
        total_time = 0
        
        for i in range(1, NUM_TESTS + 1):
            with get_driver() as driver:
                result = single_test(driver, captcha_mgr, i, use_preprocess=True)
            
            if result["status"] == "success":
                success_count += 1
            elif result["status"] == "captcha_error":
                captcha_fail_count += 1
            elif result["status"] == "ocr_fail":
                ocr_fail_count += 1
            else:
                other_fail_count += 1
            
            total_time += result.get("time", 0)
            
            # Rate limit için bekle
            if i < NUM_TESTS:
                time.sleep(0.5)
        
        # Sonuçları göster
        print("\n" + "=" * 60)
        print("📊 TEST SONUÇLARI")
        print("=" * 60)
        print(f"✅ Başarılı     : {success_count}/{NUM_TESTS} ({100*success_count/NUM_TESTS:.1f}%)")
        print(f"❌ Captcha Hata : {captcha_fail_count}/{NUM_TESTS} ({100*captcha_fail_count/NUM_TESTS:.1f}%)")
        print(f"🔴 OCR Başarısız: {ocr_fail_count}/{NUM_TESTS} ({100*ocr_fail_count/NUM_TESTS:.1f}%)")
        print(f"⚠️ Diğer Hata   : {other_fail_count}/{NUM_TESTS} ({100*other_fail_count/NUM_TESTS:.1f}%)")
        print(f"⏱️ Ort. Süre    : {total_time/NUM_TESTS:.2f} saniye")
        print("-" * 60)
        
        # Analiz
        ocr_attempted = NUM_TESTS - ocr_fail_count
        if ocr_attempted > 0:
            real_ocr_accuracy = 100 * success_count / ocr_attempted
            print(f"📈 Gerçek OCR Doğruluğu: {real_ocr_accuracy:.1f}% (OCR çalıştığında)")
        
        if success_count >= NUM_TESTS * 0.7:
            print("\n💚 OCR performansı İYİ (≥70%)")
        elif success_count >= NUM_TESTS * 0.5:
            print("\n💛 OCR performansı ORTA (50-70%) - İyileştirme gerekli")
        else:
            print("\n❤️ OCR performansı DÜŞÜK (<50%) - Acil iyileştirme gerekli")
        
        print("\n💡 Debug dosyaları 'captcha_debug' klasörüne kaydedildi.")
        
    finally:
        cleanup_driver_pool()

if __name__ == "__main__":
    main()
