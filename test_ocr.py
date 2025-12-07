"""
RapidOCR Test Script
Bu script captcha çözme başarı oranını test eder.
"""
import requests
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
import io

# --- AYARLAR ---
OCR_API_URL = "http://10.0.0.87:8000/ocr"  # config.py'den
BTK_URL = "https://internet2.btk.gov.tr/sitesorgu/"
TEST_DOMAIN = "google.com"  # Bilinen temiz domain
NUM_TESTS = 10  # Kaç test yapılacak

# Test sonuçları
results = {
    "success": 0,
    "captcha_error": 0,
    "other_error": 0,
    "total_time": 0
}

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
        img = img.point(lambda x: 0 if x < 128 else 255, '1')
        
        # BytesIO olarak döndür
        output = io.BytesIO()
        img.save(output, format='PNG')
        output.seek(0)
        return output.read()
    except Exception as e:
        print(f"Ön işleme hatası: {e}")
        return png_data

def solve_captcha(png_data: bytes, preprocess=True) -> str:
    """OCR API'ye istek at"""
    try:
        if preprocess:
            png_data = preprocess_captcha(png_data)
        
        files = {'file': ('captcha.png', png_data, 'image/png')}
        response = requests.post(OCR_API_URL, files=files, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                return result.get("text", "")
        return ""
    except Exception as e:
        print(f"OCR API hatası: {e}")
        return ""

def single_test(driver, test_num: int, use_preprocess: bool = True) -> dict:
    """Tek bir test çalıştır"""
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
        
        # OCR çöz
        captcha_text = solve_captcha(png_data, preprocess=use_preprocess)
        print(f"  [Test {test_num}] OCR Sonucu: '{captcha_text}'", end=" ")
        
        if not captcha_text or len(captcha_text) < 3:
            print("❌ OCR boş/kısa")
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
            with open(f"{debug_dir}/FAIL_captcha_{test_num}_{captcha_text}.png", 'wb') as f:
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
    print("🧪 RapidOCR Captcha Test")
    print("=" * 60)
    print(f"OCR API: {OCR_API_URL}")
    print(f"Test Sayısı: {NUM_TESTS}")
    print(f"Test Domain: {TEST_DOMAIN}")
    print("-" * 60)
    
    # API bağlantı testi
    print("\n📡 OCR API bağlantı testi...")
    try:
        # Basit bir test resmi gönder
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
        print("Lütfen OCR sunucusunun çalıştığından emin olun.")
        return
    
    # Chrome ayarları
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=options)
    
    try:
        print("\n🔄 Testler başlıyor...\n")
        
        success_count = 0
        captcha_fail_count = 0
        other_fail_count = 0
        total_time = 0
        
        for i in range(1, NUM_TESTS + 1):
            result = single_test(driver, i, use_preprocess=True)
            
            if result["status"] == "success":
                success_count += 1
            elif result["status"] == "captcha_error":
                captcha_fail_count += 1
            else:
                other_fail_count += 1
            
            total_time += result.get("time", 0)
            
            # Rate limit için bekle
            if i < NUM_TESTS:
                time.sleep(1)
        
        # Sonuçları göster
        print("\n" + "=" * 60)
        print("📊 TEST SONUÇLARI")
        print("=" * 60)
        print(f"✅ Başarılı    : {success_count}/{NUM_TESTS} ({100*success_count/NUM_TESTS:.1f}%)")
        print(f"❌ Captcha Hata: {captcha_fail_count}/{NUM_TESTS} ({100*captcha_fail_count/NUM_TESTS:.1f}%)")
        print(f"⚠️ Diğer Hata  : {other_fail_count}/{NUM_TESTS} ({100*other_fail_count/NUM_TESTS:.1f}%)")
        print(f"⏱️ Ort. Süre   : {total_time/NUM_TESTS:.2f} saniye")
        print("-" * 60)
        
        if success_count >= NUM_TESTS * 0.7:
            print("💚 OCR performansı İYİ (>70%)")
        elif success_count >= NUM_TESTS * 0.5:
            print("💛 OCR performansı ORTA (50-70%) - İyileştirme gerekli")
        else:
            print("❤️ OCR performansı DÜŞÜK (<50%) - Acil iyileştirme gerekli")
        
        print("\n💡 Başarısız captcha'lar 'captcha_debug' klasörüne kaydedildi.")
        print("   Bunları inceleyerek OCR'yi iyileştirebilirsiniz.")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
