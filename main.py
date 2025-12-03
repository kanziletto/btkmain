import threading
import time
import os
import scan_engine
import telegram_bot
import browser

def main():
    print("=" * 50)
    print("🚀 BTK Tarama Botu Başlatılıyor...")
    print("=" * 50)
    
    # 1. Driver Havuzunu Başlat
    print("\n[1/3] 🔧 Driver havuzu başlatılıyor...")
    try:
        browser.init_driver_pool()
        print("✅ Driver havuzu hazır!")
    except Exception as e:
        print(f"❌ HATA: Driver havuzu başlatılamadı: {e}")
        return
    
    # 2. Arka Plan Motoru
    print("\n[2/3] 🔄 Arka plan tarama motoru başlatılıyor...")
    scan_thread = threading.Thread(target=scan_engine.background_loop, name="BackgroundScanner")
    scan_thread.daemon = True
    scan_thread.start()
    print("✅ Motor aktif!")
    
    # 3. Telegram Botu
    print("\n[3/3] 🤖 Telegram botu başlatılıyor...")
    try:
        telegram_bot.start_polling()
    except KeyboardInterrupt:
        print("\n🛑 Durduruluyor...")
        browser.cleanup_driver_pool()
        print("✅ Çıkış yapıldı.")

if __name__ == "__main__":
    main()
