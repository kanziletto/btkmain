import threading
import time
import os
import scan_engine
import telegram_bot
import browser  # ← YENİ: Browser modülü import edildi

def main():
    print("=" * 50)
    print("🚀 BTK Tarama Botu Başlatılıyor...")
    print("=" * 50)
    
    # 0. ✅ YENİ: Driver havuzunu başlat (EN BAŞTA!)
    print("\n[1/3] 🔧 Driver havuzu başlatılıyor...")
    try:
        browser.init_driver_pool()
        print("✅ Driver havuzu hazır!")
    except Exception as e:
        print(f"❌ HATA: Driver havuzu başlatılamadı: {e}")
        print("⚠️ Chrome/ChromeDriver kurulu mu kontrol edin!")
        return
    
    # 1. Arka plan tarama motorunu başlat (Thread)
    print("\n[2/3] 🔄 Arka plan tarama motoru başlatılıyor...")
    scan_thread = threading.Thread(target=scan_engine.background_loop, name="BackgroundScanner")
    scan_thread.daemon = True
    scan_thread.start()
    print("✅ Arka plan motoru başladı!")
    
    # 2. Telegram Botunu Başlat (Ana süreç bu olacak)
    print("\n[3/3] 🤖 Telegram botu başlatılıyor...")
    print("=" * 50)
    print("✅ BOT HAZIR! Ctrl+C ile durdurun.")
    print("=" * 50)
    
    try:
        telegram_bot.start_polling()
    except KeyboardInterrupt:
        print("\n\n" + "=" * 50)
        print("🛑 Bot durduruluyor...")
        print("=" * 50)
        
        # ✅ YENİ: Temizlik yap
        print("🧹 Driver havuzu temizleniyor...")
        browser.cleanup_driver_pool()
        print("✅ Temizlik tamamlandı. Güle güle!")

if __name__ == "__main__":
    main()
