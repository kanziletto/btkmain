import telebot
from telebot import types
import telegram_config as tg_conf
from database import Database

# --- KURULUM ---
if not tg_conf.BOT_TOKEN:
    raise ValueError("BOT_TOKEN bulunamadı!")

bot = telebot.TeleBot(tg_conf.BOT_TOKEN)
db = Database()

# --- DIŞARIYA AÇILAN FONKSİYONLAR ---
def start_polling():
    print("--> Telegram Bot Başlatıldı...")
    # Komutları Telegram'a bildir
    bot.set_my_commands(tg_conf.BOT_COMMANDS)
    bot.infinity_polling()

def send_message(chat_id, text, markdown=True):
    try:
        parse_mode = "Markdown" if markdown else None
        bot.send_message(chat_id, text, parse_mode=parse_mode)
    except: pass

def send_photo(chat_id, photo, caption=None):
    try:
        bot.send_photo(chat_id, photo, caption=caption, parse_mode="Markdown")
    except: pass

def send_document(chat_id, doc, caption=None):
    try:
        bot.send_document(chat_id, doc, caption=caption)
    except: pass

# --- YARDIMCILAR ---
def check_access(func):
    def wrapper(message, *args, **kwargs):
        # Message veya CallbackQuery ayrımı
        if isinstance(message, types.CallbackQuery):
            user_id = message.message.chat.id
            obj = message
        else:
            user_id = message.chat.id
            obj = message
            
        status = db.check_user_access(user_id)
        
        if not status["access"]:
            msg = tg_conf.MESSAGES["access_denied"].format(status=status['msg'])
            if isinstance(message, types.CallbackQuery):
                bot.answer_callback_query(message.id, status['msg'], show_alert=True)
            else:
                bot.reply_to(obj, msg, parse_mode="Markdown")
            return
        return func(message, *args, **kwargs)
    return wrapper

# --- KOMUT HANDLERLARI ---
@bot.message_handler(commands=['start'])
def cmd_start(message):
    cid = message.chat.id
    is_new = db.register_user(cid)
    name = message.from_user.first_name
    
    if is_new:
        msg = tg_conf.MESSAGES["welcome_new"].format(name=name)
    else:
        msg = tg_conf.MESSAGES["welcome_old"].format(name=name)
    
    bot.send_message(cid, msg, parse_mode="Markdown", reply_markup=tg_conf.create_main_menu())

@bot.message_handler(commands=['menu'])
@check_access
def cmd_menu(message):
    bot.send_message(message.chat.id, "Ana Menü:", reply_markup=tg_conf.create_main_menu())

# DÜZELTME: SSS Komutu Eklendi
@bot.message_handler(commands=['sss'])
def cmd_faq(message):
    bot.send_message(message.chat.id, tg_conf.MESSAGES["faq"], parse_mode="Markdown")

# DÜZELTME: Destek Komutu Eklendi
@bot.message_handler(commands=['destek'])
def cmd_support(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💬 Destek / İletişim", url=tg_conf.SUPPORT_URL))
    bot.send_message(message.chat.id, "📞 İletişim için butona tıklayın:", reply_markup=markup)

@bot.message_handler(commands=['ekle'])
@check_access
def cmd_add(message):
    bot.send_message(message.chat.id, tg_conf.MESSAGES["add_prompt"])

@bot.message_handler(commands=['premium_yap'])
def cmd_premium(message):
    if str(message.chat.id) != str(tg_conf.ADMIN_ID): return
    try:
        args = message.text.split()
        if len(args) < 3: raise ValueError
        target = args[1]
        days = int(args[2])
        expiry = db.set_premium(target, days)
        bot.reply_to(message, f"✅ İşlem Tamam. Bitiş: {expiry}")
        send_message(target, f"🎉 Hesabınıza {days} gün Premium tanımlandı!")
    except: bot.reply_to(message, "Hata: /premium_yap ID GÜN")

# --- BUTON HANDLERLARI ---
@bot.callback_query_handler(func=lambda call: True)
@check_access
def handle_callback(call):
    cid = call.message.chat.id
    data = call.data
    
    # Gecikmeli import (Circular dependency önlemek için)
    import scan_engine 

    try:
        if data == "main_menu":
            bot.edit_message_text("Ana Menü:", cid, call.message.message_id, reply_markup=tg_conf.create_main_menu())
        
        elif data == "hesabim":
            u = db.get_user_data(cid)
            d = db.get_user_domains(cid)
            limit = 50 if u.get("plan") in ["premium", "admin"] else 2
            msg = tg_conf.MESSAGES["account_info"].format(
                id=cid, plan=u.get("plan", "Yok"), 
                current=len(d), limit=limit, 
                expiry=u.get("expiry_date", "-").split()[0]
            )
            bot.edit_message_text(msg, cid, call.message.message_id, reply_markup=tg_conf.create_main_menu(), parse_mode="Markdown")
        
        elif data == "listem" or data == "refresh_list":
            domains = db.get_user_domains(cid)
            if not domains:
                bot.answer_callback_query(call.id, "Liste boş!")
                return
            
            info_list = []
            for d in domains:
                st, tm = db.get_domain_info(d)
                info_list.append((d, st, tm))
            
            markup = tg_conf.create_domain_list_menu(info_list)
            try:
                bot.edit_message_text("📄 **Domainleriniz:**", cid, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
            except: 
                # Mesaj aynıysa hata verebilir, yutuyoruz.
                pass
        
        # DÜZELTME: SSS Butonu İşlevi
        elif data == "sss":
            bot.send_message(cid, tg_conf.MESSAGES["faq"], parse_mode="Markdown")
            bot.answer_callback_query(call.id)

        # DÜZELTME: Sorgu Butonu İşlevi
        elif data == "sorgu":
            user_data = db.get_user_data(cid)
            # Sadece Premium ve Admin kullanabilir
            if user_data.get("plan") not in ["premium", "admin"]:
                bot.answer_callback_query(call.id, "⛔ Sadece Premium!", show_alert=True)
                bot.send_message(cid, tg_conf.MESSAGES["only_premium"])
                return
            
            domains = db.get_user_domains(cid)
            if not domains:
                bot.answer_callback_query(call.id, "Liste boş!")
                return

            bot.answer_callback_query(call.id, "Tarama başlatılıyor...")
            scan_engine.start_manual_scan(cid, domains)

        elif data.startswith("manage_"):
            domain = data.replace("manage_", "")
            st, tm = db.get_domain_info(domain)
            u = db.get_user_data(cid)
            is_prem = u.get("plan") in ["premium", "admin"]
            markup = tg_conf.create_domain_manage_menu(domain, is_prem)
            msg = f"🌐 **{domain}**\n💡 Durum: {st}\n🕒 Son: {tm}"
            bot.edit_message_text(msg, cid, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        
        elif data.startswith("scan_"):
            domain = data.replace("scan_", "")
            bot.answer_callback_query(call.id, "Tarama başladı...")
            scan_engine.start_manual_scan(cid, [domain])
            
        elif data.startswith("del_confirm_"):
            domain = data.replace("del_confirm_", "")
            db.sil_domain(cid, domain)
            bot.answer_callback_query(call.id, "Silindi.")
            call.data = "listem"
            handle_callback(call)

        elif data == "sil_menu":
            doms = db.get_user_domains(cid)
            markup = tg_conf.create_delete_menu(doms)
            bot.edit_message_text("🗑️ Silinecek domaini seçin:", cid, call.message.message_id, reply_markup=markup)
        
        elif data == "ekle":
            bot.send_message(cid, tg_conf.MESSAGES["add_prompt"])
            
    except Exception as e:
        print(f"Callback Hata: {e}")

# --- METİN VE DOSYA İŞLEME ---
@bot.message_handler(content_types=['document'])
@check_access
def handle_docs(message):
    import scan_engine
    cid = message.chat.id
    try:
        file_info = bot.get_file(message.document.file_id)
        content = bot.download_file(file_info.file_path).decode('utf-8')
        
        u = db.get_user_data(cid)
        cur = len(db.get_user_domains(cid))
        limit = 50 if u.get("plan") in ["premium", "admin"] else 2
        
        added = []
        for line in content.splitlines():
            for part in line.replace(',', ' ').split():
                d = part.strip()
                if len(d) > 3 and "." in d:
                    if cur < limit:
                        if db.ekle_domain(cid, d):
                            added.append(d)
                            cur += 1
        
        if added:
            bot.reply_to(message, f"✅ {len(added)} domain eklendi.", reply_markup=tg_conf.create_main_menu())
            scan_engine.start_manual_scan(cid, added)
        else:
            bot.reply_to(message, "⚠️ Ekleme yapılamadı (Limit veya Hata).")

    except: pass

@bot.message_handler(func=lambda message: True)
@check_access
def handle_text(message):
    import scan_engine
    cid = message.chat.id
    text = message.text
    
    u = db.get_user_data(cid)
    cur = len(db.get_user_domains(cid))
    limit = 50 if u.get("plan") in ["premium", "admin"] else 2
    
    added = []
    potential_domains = text.replace(',', ' ').split()
    
    for d in potential_domains:
        clean = d.strip()
        if len(clean) > 3 and "." in clean and not clean.startswith("/"):
            if cur < limit:
                if db.ekle_domain(cid, clean):
                    added.append(clean)
                    cur += 1
    
    if added:
        bot.reply_to(message, f"✅ {len(added)} domain eklendi.", reply_markup=tg_conf.create_main_menu())
        scan_engine.start_manual_scan(cid, added)
    elif not text.startswith("/"):
        bot.reply_to(message, "⚠️ Anlaşılmadı. Domain eklemek için domain adını yazın.", reply_markup=tg_conf.create_main_menu())
