#!/usr/bin/env python3
"""
Captcha Başarı Oranı Test Scripti
Kullanım: python test_captcha_rate.py [test_sayisi]
"""

import sys
import time
from btk import BTKScanner
from browser import get_driver

def test_captcha_rate(test_count=20):
    """Belirtilen sayıda captcha çözümü test eder ve başarı oranını hesaplar"""
    
    test_domain = "google.com"  # Test için güvenli domain
    scanner = BTKScanner()
    
    success = 0
    fail = 0
    times = []
    
    print(f"\n{'='*50}")
    print(f"🧪 CAPTCHA BAŞARI ORANI TESTİ")
    print(f"📊 Test Sayısı: {test_count}")
    print(f"{'='*50}\n")
    
    with get_driver() as driver:
        driver.get(scanner.base_url)
        time.sleep(2)
        
        for i in range(1, test_count + 1):
            start = time.time()
            
            try:
                # Tek sorgu yap (retry olmadan)
                result = scanner._tek_sorgu(test_domain, driver)
                elapsed = round(time.time() - start, 2)
                times.append(elapsed)
                
                if result.durum != "HATA":
                    success += 1
                    icon = "✅"
                    status = result.durum
                else:
                    fail += 1
                    icon = "❌"
                    status = result.detay
                
                rate = (success / i) * 100
                print(f"[{i:02d}/{test_count}] {icon} {status:<20} | ⏱️ {elapsed}s | Başarı: %{rate:.1f}")
                
                # Sayfa yenile (yeni captcha)
                driver.get(scanner.base_url)
                time.sleep(0.5)
                
            except Exception as e:
                fail += 1
                print(f"[{i:02d}/{test_count}] ❌ HATA: {e}")
    
    # ÖZET
    rate = (success / test_count) * 100
    avg_time = sum(times) / len(times) if times else 0
    
    print(f"\n{'='*50}")
    print(f"📊 SONUÇLAR")
    print(f"{'='*50}")
    print(f"✅ Başarılı: {success}/{test_count}")
    print(f"❌ Başarısız: {fail}/{test_count}")
    print(f"📈 Başarı Oranı: %{rate:.1f}")
    print(f"⏱️ Ortalama Süre: {avg_time:.2f}s")
    print(f"{'='*50}\n")
    
    # Değerlendirme
    if rate >= 80:
        print("🎉 Mükemmel! Captcha çözümü çok iyi çalışıyor.")
    elif rate >= 60:
        print("👍 İyi. Kabul edilebilir seviyede.")
    elif rate >= 40:
        print("⚠️ Orta. İyileştirme gerekebilir.")
    else:
        print("❌ Düşük! Captcha sağlayıcı veya preprocessing kontrol edilmeli.")

if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    test_captcha_rate(count)
