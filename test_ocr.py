"""
RapidOCR Test Script - browser.py kullanır
"""
import time
import os
import io
import requests
from PIL import Image
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Bot modülleri
from browser import init_driver_pool, get_driver, cleanup_driver_pool
from config import OCR_API_URL

# --- AYARLAR ---
BTK_URL = "https://internet2.btk.gov.tr/sitesorgu/"
TEST_DOMAIN = "google.com"
NUM_TESTS = 10

def preprocess_captcha(png_data: bytes) -> bytes:
    """Captcha ön işleme - sadece büyütme"""
    try:
        img = Image.open(io.BytesIO(png_data))
        w, h = img.size
        
        # 1. Kenar kırpma
        img = img.crop((2, 2, w - 2, h - 2))
        
        # 2. Büyütme (4x)
        new_w, new_h = img.size
        img = img.resize((new_w * 4, new_h * 4), Image.Resampling.LANCZOS)
        
        output = io.BytesIO()
        img.save(output, format='PNG')
        output.seek(0)
        return output.read()
    except:
        return png_data

def solve_captcha(png_data: bytes) -> str:
    """OCR API'ye istek"""
    try:
        files = {'file': ('captcha.png', png_data, 'image/png')}
        response = requests.post(OCR_API_URL, files=files, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                return result.get("text", "")
        return ""
    except:
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
        
        png_data = captcha_img.screenshot_as_png
        
        # Debug kaydet
        debug_dir = "captcha_debug"
        os.makedirs(debug_dir, exist_ok=True)
        with open(f"{debug_dir}/captcha_{test_num}.png", 'wb') as f:
            f.write(png_data)
        
        # Ön işle ve çöz
        processed = preprocess_captcha(png_data)
        with open(f"{debug_dir}/captcha_{test_num}_proc.png", 'wb') as f:
            f.write(processed)
        
        captcha_text = solve_captcha(processed)
        
        print(f"  [{test_num:02d}] OCR: '{captcha_text}'", end=" ")
        
        if not captcha_text or len(captcha_text) < 3:
            print("❌ OCR boş")
            return {"status": "ocr_fail"}
        
        input_domain.clear()
        input_domain.send_keys(TEST_DOMAIN)
        input_captcha.clear()
        input_captcha.send_keys(captcha_text)
        btn_submit.click()
        
        time.sleep(2)
        page = driver.page_source.lower()
        
        if "yanlış girdiniz" in page or "hatalı" in page:
            print("❌ Yanlış")
            with open(f"{debug_dir}/FAIL_{test_num}_{captcha_text}.png", 'wb') as f:
                f.write(png_data)
            return {"status": "captcha_error", "ocr": captcha_text}
        
        elif "bulunamadı" in page or "engellenmiştir" in page:
            print("✅ Başarılı!")
            return {"status": "success", "ocr": captcha_text}
        
        else:
            print("⚠️ Bilinmeyen")
            return {"status": "unknown"}
            
    except Exception as e:
        print(f"❌ {str(e)[:40]}")
        return {"status": "error"}

def main():
    print("=" * 50)
    print("🧪 RapidOCR Captcha Test")
    print("=" * 50)
    print(f"OCR: {OCR_API_URL}")
    print(f"Test: {NUM_TESTS} adet")
    print("-" * 50)
    
    # API test
    print("\n📡 OCR API...")
    try:
        img = Image.new('RGB', (100, 40), 'white')
        buf = io.BytesIO()
        img.save(buf, 'PNG')
        buf.seek(0)
        r = requests.post(OCR_API_URL, files={'file': ('t.png', buf, 'image/png')}, timeout=5)
        print("✅ OK!" if r.status_code == 200 else f"❌ HTTP {r.status_code}")
        if r.status_code != 200:
            return
    except Exception as e:
        print(f"❌ {e}")
        return
    
    # Driver havuzu
    print("\n🔧 Chrome başlatılıyor...")
    init_driver_pool()
    
    print("\n🔄 Testler:\n")
    
    success = captcha_fail = ocr_fail = other = 0
    
    try:
        for i in range(1, NUM_TESTS + 1):
            with get_driver() as driver:
                result = single_test(driver, i)
            
            s = result["status"]
            if s == "success": success += 1
            elif s == "captcha_error": captcha_fail += 1
            elif s == "ocr_fail": ocr_fail += 1
            else: other += 1
            
            time.sleep(0.3)
    
    finally:
        cleanup_driver_pool()
    
    # Sonuç
    print("\n" + "=" * 50)
    print("📊 SONUÇ")
    print("=" * 50)
    print(f"✅ Başarılı   : {success}/{NUM_TESTS} ({100*success//NUM_TESTS}%)")
    print(f"❌ Yanlış OCR : {captcha_fail}")
    print(f"🔴 OCR Boş    : {ocr_fail}")
    print(f"⚠️ Diğer      : {other}")
    
    if success >= 6:
        print("\n💚 OCR İYİ!")
    elif success >= 4:
        print("\n💛 OCR ORTA")
    else:
        print("\n❤️ OCR ZAYIF")
    
    print(f"\n📁 Debug: captcha_debug/")

if __name__ == "__main__":
    main()
