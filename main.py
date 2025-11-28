import threading
import time
import os
import scan_engine
import telegram_bot

def main():
    # 1. Arka plan tarama motorunu başlat (Thread)
    scan_thread = threading.Thread(target=scan_engine.background_loop)
    scan_thread.daemon = True
    scan_thread.start()
    
    # 2. Telegram Botunu Başlat (Ana süreç bu olacak)
    # Bot polling işlemi bu thread'i bloklar ve canlı tutar.
    try:
        telegram_bot.start_polling()
    except KeyboardInterrupt:
        print("\n🛑 Bot durduruluyor...")

if __name__ == "__main__":
    main()
