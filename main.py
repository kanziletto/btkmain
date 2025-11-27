import asyncio
import os
from telebot.async_telebot import AsyncTeleBot
from config import BOT_TOKEN
from database import Database
from btk import BTKScanner
from utils import logger

bot = AsyncTeleBot(BOT_TOKEN)
db = Database()
scanner = BTKScanner()

# --- STANDART KOMUTLAR ---
@bot.message_handler(commands=['start'])
async def send_welcome(message):
    await bot.reply_to(message, "Bot Aktif 🛠️\nKomutlar:\n/ekle domain.com\n/sil domain.com\n/sorgu (Manuel Test)")

@bot.message_handler(commands=['ekle'])
async def add_domain(message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await bot.reply_to(message, "Hata: /ekle domain.com şeklinde yazın.")
            return
        domain = parts[1]
        if db.ekle_domain(message.chat.id, domain):
            await bot.reply_to(message, f"✅ {domain} eklendi.")
        else:
            await bot.reply_to(message, f"⚠️ {domain} zaten listede.")
    except Exception as e:
        await bot.reply_to(message, f"Hata: {e}")

@bot.message_handler(commands=['sil'])
async def remove_domain(message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await bot.reply_to(message, "Hata: /sil domain.com şeklinde yazın.")
            return
        domain = parts[1]
        if db.sil_domain(message.chat.id, domain):
            await bot.reply_to(message, f"🗑️ {domain} silindi.")
        else:
            await bot.reply_to(message, f"⚠️ {domain} listede yok.")
    except Exception as e:
        await bot.reply_to(message, f"Hata: {e}")

async def raporla_ve_gonder(chat_id, domain, sonuc):
    """Sonuç metnini ve fotoğrafları gönderen yardımcı fonksiyon"""
    
    # 1. Metin Raporu
    text = f"📊 **{domain}**\nDurum: {sonuc.durum}\nCaptcha: {sonuc.captcha_text}\nSüre: {sonuc.sure}sn"
    try:
        await bot.send_message(chat_id, text)
    except Exception as e:
        logger.error(f"Mesaj gönderme hatası: {e}")

    # 2. Fotoğraf Raporu (4 Adım)
    if sonuc.screenshot_paths:
        for i, path in enumerate(sonuc.screenshot_paths):
            if os.path.exists(path):
                try:
                    # Fotoğraflara açıklama ekleyelim
                    caption = ""
                    if "orj" in path: caption = "1. Sayfa Açılışı (Boş)"
                    elif "proc" in path: caption = "2. İşlenmiş Captcha (API'den Gelen)"
                    elif "yazilan" in path: caption = f"3. Kutuya Yazılan: {sonuc.captcha_text}"
                    elif "sonuc" in path: caption = f"4. Sonuç Ekranı: {sonuc.durum}"
                    
                    with open(path, 'rb') as photo:
                        await bot.send_photo(chat_id, photo, caption=caption)
                except Exception as e:
                    logger.error(f"Fotoğraf gönderme hatası ({path}): {e}")
                finally:
                    # Gönderdikten sonra sil (Diski doldurmasın)
                    try:
                        os.remove(path)
                    except:
                        pass

@bot.message_handler(commands=['sorgu'])
async def manual_check(message):
    domains = db.get_user_domains(message.chat.id)
    if not domains:
        await bot.reply_to(message, "Listeniz boş. Önce /ekle ile domain ekleyin.")
        return

    await bot.reply_to(message, f"🔍 {len(domains)} adet domain taranıyor... (Fotoğraflar geliyor)")
    
    for domain in domains:
        loop = asyncio.get_running_loop()
        sonuc = await loop.run_in_executor(None, scanner.sorgula, domain)
        await raporla_ve_gonder(message.chat.id, domain, sonuc)

# --- OTOMATİK LOOP ---
async def background_loop():
    while True:
        logger.info("[OTO] Otomatik Tarama Döngüsü...")
        all_data = db.get_all_users_domains()
        
        if not all_data:
            await asyncio.sleep(60)
            continue

        for chat_id, domains in all_data.items():
            for domain in domains:
                loop = asyncio.get_running_loop()
                sonuc = await loop.run_in_executor(None, scanner.sorgula, domain)
                
                # Otomatik modda da fotoğrafları görmek istiyorsanız:
                await raporla_ve_gonder(chat_id, domain, sonuc)
                
                await asyncio.sleep(5) 
        
        await asyncio.sleep(300) # 5 Dakika bekle

async def main():
    asyncio.create_task(background_loop())
    await bot.polling()

if __name__ == "__main__":
    asyncio.run(main())
