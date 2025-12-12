import requests
import time
from datetime import datetime

URL = "https://internet2.btk.gov.tr/sitesorgu/"

def check_health():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🩺 BTK Sağlık Kontrolü Başlatılıyor...")
    print(f"👉 Hedef: {URL}")
    
    try:
        start = time.time()
        # Proxy ayarları ortam değişkeninden veya config'den alınabilir, 
        # şimdilik direkt bağlantı (veya sistem proxy'si) deneniyor.
        response = requests.get(URL, timeout=10, verify=False) 
        duration = round(time.time() - start, 2)
        
        if response.status_code == 200:
            print(f"✅ BAŞARILI! (Süre: {duration}s)")
            print(f"📊 Durum Kodu: {response.status_code}")
            if "Sorgulamak istediğiniz web adresini giriniz" in response.text:
                print("📝 Form içeriği doğrulandı.")
            else:
                print("⚠️ Sayfa açıldı ama form içeriği bulunamadı (Bot koruması olabilir).")
        else:
            print(f"❌ SORUN VAR! İstek gitti ama hata döndü.")
            print(f"Durum Kodu: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ BAŞARISIZ: Bağlantı Hatası (Connection Error).")
        print("👉 İnternet bağlantınızı veya Proxy/VPN ayarlarınızı kontrol edin.")
    except requests.exceptions.Timeout:
        print("❌ BAŞARISIZ: Zaman Aşımı (Timeout).")
        print("👉 Site çok yavaş veya erişilemiyor.")
    except Exception as e:
        print(f"❌ BEKLENMEYEN HATA: {e}")

if __name__ == "__main__":
    # Uyarı: SSL sertifika hatalarını yoksaymak için (BTK bazen sertifika hatası verebilir)
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    check_health()
