import requests
import time
from datetime import datetime
import urllib3
import sys
import os

# Config.py'nin bulundugu dizini path'e ekle
sys.path.append(os.getcwd())

try:
    from config import PROXY_LIST
except ImportError:
    print("UYARI: config.py bulunamadi veya PROXY_LIST icermiyor.")
    PROXY_LIST = []

URL = "https://internet2.btk.gov.tr/sitesorgu/"
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def check_btk_health():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] BTK PROXY SAGLIK KONTROLU BASLATILIYOR...")
    print(f"HEDEF: {URL}")
    print("--------------------------------------------------")
    
    if not PROXY_LIST:
        print("HATA: Test edilecek proxy bulunamadi.")
        return

    working_count = 0
    failed_count = 0
    total = len(PROXY_LIST)

    for i, proxy_addr in enumerate(PROXY_LIST):
        proxy_url = f"http://{proxy_addr}" if not proxy_addr.startswith("http") else proxy_addr
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        
        print(f"[{i+1}/{total}] Test ediliyor: {proxy_addr} ... ", end="", flush=True)
        
        try:
            start = time.time()
            response = requests.get(URL, proxies=proxies, timeout=10, verify=False)
            duration = round(time.time() - start, 2)
            
            if response.status_code == 200:
                print(f"BASARILI (Sure: {duration}s)")
                working_count += 1
            else:
                print(f"HATA (Kod: {response.status_code})")
                failed_count += 1
                
        except requests.exceptions.ProxyError:
            print("BASARISIZ (Proxy Hatasi)")
            failed_count += 1
        except requests.exceptions.ConnectTimeout:
            print("BASARISIZ (Zaman Asimi)")
            failed_count += 1
        except requests.exceptions.ReadTimeout:
            print("BASARISIZ (Okuma Zaman Asimi)")
            failed_count += 1
        except Exception as e:
            print(f"BASARISIZ (Hata: {str(e)[:50]})")
            failed_count += 1

    print("--------------------------------------------------")
    print(f"TAMAMLANDI.")
    print(f"CALISAN: {working_count}")
    print(f"BOZUK:   {failed_count}")
    print(f"TOPLAM:  {total}")

if __name__ == "__main__":
    check_btk_health()
