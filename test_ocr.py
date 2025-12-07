"""
RapidOCR Basit Test Script
Driver havuzunu kullanmaz, kendi Chrome'unu başlatır.
"""
import time
import os
import io
import requests
from PIL import Image

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Config'den OCR URL'i al
try:
    from config import OCR_API_URL
except:
    OCR_API_URL = "http://10.0.0.87:8000/ocr"

# --- AYARLAR ---
BTK_URL = "https://internet2.btk.gov.tr/sitesorgu/"
TEST_DOMAIN = "google.com"
NUM_TESTS = 10

def create_driver():
    """Basit bir Chrome driver oluştur"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")
    
    driver = webdriver.Chrome(service=Service(), options=options)
    driver.set_page_load_timeout(20)
    return driver

def preprocess_captcha(png_data: bytes) -> bytes:
    """Captcha ön işleme"""
    try:
        img = Image.open(io.BytesIO(png_data))
        w, h = img.size
        img = img.crop((2, 2, w - 2, h - 2))
        new_w, new_h = img.size
        img = img.resize((new_w * 2, new_h * 2), Image.Resampling.LANCZOS)
        img = img.convert('L')
        img = img.point(lambda x: 0 if x < 140 else 255, '1')
        output = io.BytesIO()
        img.save(output, format='PNG')
        output.seek(0)
        return output.read()
    except Exception as e:
        print(f"Ön işleme hatası: {e}")
        return png_data

def solve_captcha(png_data: bytes) -> str:
    """OCR API'ye istek at"""
    try:
        files = {'file': ('captcha.png', png_data, 'image/png')}
        response = requests.post(OCR_API_URL, files=files, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                return result.get("text", "")
        return ""
    except Exception as e:
        print(f"OCR hatası: {e}")
        return ""

def single_test(driver, test_num: int) -> dict:
    """Tek test"""
    start = time.time()
    
    try:
        driver.get(BTK_URL)
        wait = WebDriverWait(driver, 15)
        
        input_domain = wait.until(EC.visibility_of_element_located((By.ID, "deger")))
        input_captcha = driver.find_element(By.ID, "security_code")
        captcha_img = wait.until(EC.visibility_of_element_located((By.ID, "security_code_image")))
        btn_submit = driver.find_element(By.ID, "submit1")
        
        # Captcha al
        png_data = captcha_img.screenshot_as_png
        
        # Debug kaydet
        debug_dir = "captcha_debug"
        os.makedirs(debug_dir, exist_ok=True)
        with open(f"{debug_dir}/captcha_{test_num}.png", 'wb') as f:
            f.write(png_data)
        
        # Ön işle ve çöz
        processed = preprocess_captcha(png_data)
        captcha_text = solve_captcha(processed)
        
        print(f"  [Test {test_num}] OCR: '{captcha_text}'", end=" ")
        
        if not captcha_text or len(captcha_text) < 3:
            print("❌ OCR boş")
            return {"status": "ocr_fail", "time": time.time() - start}
        
        # Form doldur
        input_domain.clear()
        input_domain.send_keys(TEST_DOMAIN)
        input_captcha.clear()
        input_captcha.send_keys(captcha_text)
        btn_submit.click()
        
        time.sleep(2)
        page_source = driver.page_source.lower()
        
        if "yanlış girdiniz" in page_source or "hatalı" in page_source:
            print("❌ Yanlış")
            with open(f"{debug_dir}/FAIL_{test_num}_{captcha_text}.png", 'wb') as f:
                f.write(png_data)
            return {"status": "captcha_error", "time": time.time() - start}
        
        elif "bulunamadı" in page_source or "engellenmiştir" in page_source:
            print("✅ Başarılı!")
            return {"status": "success", "time": time.time() - start}
        
        else:
            print("⚠️ Bilinmeyen")
            return {"status": "unknown", "time": time.time() - start}
            
    except Exception as e:
        print(f"❌ Hata: {str(e)[:50]}")
        return {"status": "error", "time": time.time() - start}

def main():
    print("=" * 60)
    print("🧪 RapidOCR Basit Test")
    print("=" * 60)
    print(f"OCR API: {OCR_API_URL}")
    print(f"Test Sayısı: {NUM_TESTS}")
    print("-" * 60)
    
    # API test
    print("\n📡 OCR API testi...")
    try:
        test_img = Image.new('RGB', (100, 40), color='white')
        img_bytes = io.BytesIO()
        test_img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        response = requests.post(OCR_API_URL, files={'file': ('test.png', img_bytes, 'image/png')}, timeout=5)
        if response.status_code == 200:
            print("✅ OCR API OK!")
        else:
            print(f"❌ HTTP {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Bağlantı hatası: {e}")
        return
    
    # Chrome başlat
    print("\n🔧 Chrome başlatılıyor...")
    try:
        driver = create_driver()
        print("✅ Chrome hazır!")
    except Exception as e:
        print(f"❌ Chrome hatası: {e}")
        print("\n💡 Çözüm:")
        print("   sudo apt update")
        print("   sudo apt install -y chromium-browser chromium-chromedriver")
        return
    
    try:
        print("\n🔄 Testler başlıyor...\n")
        
        success = 0
        captcha_fail = 0
        ocr_fail = 0
        other = 0
        total_time = 0
        
        for i in range(1, NUM_TESTS + 1):
            result = single_test(driver, i)
            
            if result["status"] == "success":
                success += 1
            elif result["status"] == "captcha_error":
                captcha_fail += 1
            elif result["status"] == "ocr_fail":
                ocr_fail += 1
            else:
                other += 1
            
            total_time += result.get("time", 0)
            
            if i < NUM_TESTS:
                time.sleep(0.5)
        
        # Sonuçlar
        print("\n" + "=" * 60)
        print("📊 SONUÇLAR")
        print("=" * 60)
        print(f"✅ Başarılı    : {success}/{NUM_TESTS} ({100*success/NUM_TESTS:.0f}%)")
        print(f"❌ Yanlış OCR  : {captcha_fail}/{NUM_TESTS}")
        print(f"🔴 OCR Çalışmadı: {ocr_fail}/{NUM_TESTS}")
        print(f"⚠️ Diğer      : {other}/{NUM_TESTS}")
        print(f"⏱️ Ort. Süre  : {total_time/NUM_TESTS:.1f}s")
        print("-" * 60)
        
        if success >= NUM_TESTS * 0.6:
            print("💚 OCR İYİ!")
        elif success >= NUM_TESTS * 0.4:
            print("💛 OCR ORTA - iyileştirme gerekli")
        else:
            print("❤️ OCR ZAYIF - acil müdahale gerekli")
        
    finally:
        driver.quit()
        print("\n✅ Chrome kapatıldı.")

if __name__ == "__main__":
    main()
