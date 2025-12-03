import telebot
from telebot import types
import telegram_config as tg_conf
from database import Database
from config import BOT_TOKEN, ADMIN_ID, ADMIN_CHANNEL_ID
import datetime
import os
import requests

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN bulunamadı!")

bot = telebot.TeleBot(BOT_TOKEN)
db = Database()

def start_polling():
    print("--> Telegram Bot Başlatıldı...")
    bot.set_my_commands(tg_conf.BOT_COMMANDS)
    bot.infinity_polling()

# --- YARDIMCI FONKSİYONLAR ---

def send_message(chat_id, text, markdown=True):
    try:
        parse_mode = "Markdown" if markdown else None
        bot.send_message(chat_id, text, parse_mode=parse_mode)
    except Exception as e:
        print(f"❌ Mesaj Hatası ({chat_id}): {e}")

def send_photo(chat_id, photo, caption=None):
    try: bot.send_photo(chat_id, photo, caption=caption, parse_mode="Markdown")
    except: pass

def send_document(chat_id, doc, caption=None):
    try: bot.send_document(chat_id, doc, caption=caption)
    except: pass

def check_access(func):
    def wrapper(message, *args, **kwargs):
        # Callback ve Message ayrımı
        if isinstance(message, types.CallbackQuery):
            user_id = message.message.chat.id
        else:
            user_id = message.chat.id
            
        status = db.check_user_access(user_id)
        
        if not status["access"]:
            msg = tg_conf.MESSAGES["access_denied"].format(status=status['msg'])
            if isinstance(message, types.CallbackQuery):
                bot.answer_callback_query(message.id, status['msg'], show_alert=True)
            else:
                bot.reply_to(message, msg, parse_mode="Markdown")
            return
        return func(message, *args, **kwargs)
    return wrapper

user_adding_domain = set()

# --- MENÜ FONKSİYONLARI ---

def _show_account_menu(cid, message_obj=None, is_edit=False):
    """Hesabım menüsünü oluşturur ve gönderir/düzenler"""
    u = db.get_user_data(cid)
    d = db.get_user_domains(cid)
    
    plan = u.get("plan")
    # Ultra üyeler için limit 100, diğerleri için standart
    limit = 100 if plan == "ultra" else (50 if plan in ["premium", "admin"] else 2)
    
    msg = tg_conf.MESSAGES["account_info"].format(
        id=cid, 
        plan=plan if plan else "Yok", 
        current=len(d), 
        limit=limit, 
        expiry=u.get("expiry_date", "-")[:10]
    )
    
    markup = tg_conf.create_main_menu()
    
    # Ultra üyeler için özel buton
    if plan == "ultra":
        is_active = u.get("ultra_enabled", True)
        btn_text = "📸 Ultra Foto: ✅ AÇIK" if is_active else "📸 Ultra Foto: ❌ KAPALI"
        # En üste ekle
        markup.keyboard.insert(0, [types.InlineKeyboardButton(btn_text, callback_data="toggle_ultra_mode")])

    if is_edit and message_obj:
        try:
            bot.edit_message_text(msg, cid, message_obj.message_id, reply_markup=markup, parse_mode="Markdown")
        except Exception as e:
            # "message is not modified" hatasını yoksay
            if "message is not modified" not in str(e):
                print(f"Menu edit hatası: {e}")
    else:
        bot.send_message(cid, msg, parse_mode="Markdown", reply_markup=markup)

def _show_webhook_list(chat_id, message_id=None):
    """Webhook listesini gösterir"""
    try:
        webhooks = db.get_webhooks(ADMIN_ID)
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        if not webhooks:
            text = "📂 **Webhook Listesi**\n\nHenüz ekli bir webhook yok."
        else:
            text = "📂 **Webhook Listesi**\nDüzenlemek için seçiniz:"
            for wh in webhooks:
                status_icon = "🟢" if wh["active"] else "🔴"
                domain_count = len(wh['domains'])
                btn_text = f"{status_icon} {wh['name']} ({domain_count} Domain)"
                markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"wh_detail_{wh['id']}"))
        
        markup.add(types.InlineKeyboardButton("➕ Yeni Webhook Ekle", callback_data="wh_add_new"))
        
        if message_id:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Hata: {e}")

# --- KULLANICI KOMUTLARI ---

@bot.message_handler(commands=['start'])
def cmd_start(message):
    cid = message.chat.id
    name = message.from_user.first_name
    
    conn = db._get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (str(cid),))
    existing = c.fetchone()
    conn.close()
    
    if existing:
        bot.send_message(cid, tg_conf.MESSAGES["welcome_old"].format(name=name), reply_markup=tg_conf.create_main_menu())
    else:
        # Hafta sonu kontrolü
        is_weekend = datetime.datetime.now().weekday() >= 5
        
        if is_weekend:
            bot.send_message(cid, tg_conf.MESSAGES["welcome_new"].format(name=name), 
                             parse_mode="Markdown", reply_markup=tg_conf.create_trial_choice_menu(is_weekend))
        else:
            # Hafta içi direkt başlat
            succ, st, ex = db.register_user_scheduled(cid, False)
            if succ:
                welcome_msg = tg_conf.MESSAGES["welcome_new"].format(name=name)
                start_msg = tg_conf.MESSAGES["trial_started_now"].format(
                    start_date=st.strftime("%d.%m.%Y %H:%M"), 
                    expiry_date=ex.strftime("%d.%m.%Y %H:%M")
                )
                bot.send_message(cid, welcome_msg, parse_mode="Markdown")
                bot.send_message(cid, start_msg, parse_mode="Markdown", reply_markup=tg_conf.create_main_menu())
            else:
                bot.send_message(cid, "Bir hata oluştu veya zaten kayıtlısınız.", reply_markup=tg_conf.create_main_menu())

@bot.message_handler(commands=['menu'])
@check_access
def cmd_menu(message):
    bot.send_message(message.chat.id, "📋 **Ana Menü:**", parse_mode="Markdown", reply_markup=tg_conf.create_main_menu())

@bot.message_handler(commands=['sss'])
def cmd_faq(message):
    bot.send_message(message.chat.id, tg_conf.MESSAGES["faq"], parse_mode="Markdown")

@bot.message_handler(commands=['ekle'])
@check_access
def cmd_add(message):
    user_adding_domain.add(message.chat.id)
    bot.send_message(message.chat.id, tg_conf.MESSAGES["add_prompt"], parse_mode="Markdown")

@bot.message_handler(commands=['hesabim'])
@check_access
def cmd_account(message):
    _show_account_menu(message.chat.id)

@bot.message_handler(commands=['listem'])
@check_access
def cmd_list(message):
    cid = message.chat.id
    domains = db.get_user_domains(cid)
    if not domains:
        bot.send_message(cid, tg_conf.MESSAGES["list_empty"], reply_markup=tg_conf.create_main_menu())
        return
    info = [(d, *db.get_domain_info(d)) for d in domains]
    bot.send_message(cid, "📄 **Domainleriniz:**", parse_mode="Markdown", reply_markup=tg_conf.create_domain_list_menu(info))

@bot.message_handler(commands=['sorgu'])
@check_access
def cmd_query(message):
    import scan_engine
    cid = message.chat.id
    u = db.get_user_data(cid)
    
    # İzin kontrolü (Ultra dahil)
    if u.get("plan") not in ["premium", "admin", "ultra"]:
        bot.send_message(cid, tg_conf.MESSAGES["only_premium"])
        return
    
    domains = db.get_user_domains(cid)
    if not domains:
        bot.send_message(cid, "⚠️ Liste boş.", reply_markup=tg_conf.create_main_menu())
        return
    scan_engine.start_manual_scan(cid, domains)

@bot.message_handler(commands=['destek'])
def cmd_support(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💬 Destek / İletişim", url=tg_conf.SUPPORT_URL))
    bot.send_message(message.chat.id, "📞 İletişim için butona tıklayın:", reply_markup=markup)

# --- ADMIN KOMUTLARI ---

@bot.message_handler(commands=['webhooks'])
def cmd_webhooks(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    _show_webhook_list(message.chat.id)

@bot.message_handler(commands=['webhook_ekle'])
def cmd_webhook_add(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    try:
        parts = message.text.split(maxsplit=4)
        if len(parts) < 5:
            bot.reply_to(message, "❌ Format: `/webhook_ekle <isim> <url> <domainler> <gün>`\nÖrn: `/webhook_ekle Slack https://... * 365`", parse_mode="Markdown")
            return
        name, url, domains_str, days = parts[1], parts[2], parts[3], int(parts[4])
        domains = ["*"] if domains_str == "*" else [d.strip().lower() for d in domains_str.split(",")]
        
        wid = db.add_webhook(ADMIN_ID, name, url, domains, days)
        bot.reply_to(message, f"✅ Webhook eklendi! ID: {wid}")
        
        # Test mesajı
        try: requests.post(url, json={"text": f"✅ Webhook Eklendi: {name}"}, timeout=5)
        except: bot.send_message(message.chat.id, "⚠️ Test mesajı gönderilemedi.")
    except Exception as e:
        bot.reply_to(message, f"Hata: {e}")

@bot.message_handler(commands=['db_export'])
def cmd_db_export(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    try:
        bot.send_message(message.chat.id, "⏳ Veritabanı export ediliyor...")
        export_data = db.export_all_data()
        filename = f"db_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(filename, "w", encoding="utf-8") as f: f.write(export_data)
        with open(filename, "rb") as f: bot.send_document(ADMIN_CHANNEL_ID, f, caption="📊 **Veritabanı Export**")
        os.remove(filename)
        bot.send_message(message.chat.id, "✅ Export Admin Kanalı'na gönderildi.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Hata: {e}")

@bot.message_handler(commands=['premium_yap'])
def cmd_premium(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    try:
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, "❌ Kullanım: `/premium_yap <USER_ID> <GÜN>`", parse_mode="Markdown")
            return
        target_id, days = args[1], int(args[2])
        expiry = db.set_premium(target_id, days)
        bot.reply_to(message, f"✅ {target_id} için {days} gün Premium tanımlandı.\n📅 Bitiş: {expiry}")
        try: bot.send_message(target_id, f"🎉 Hesabınıza **{days} gün** Premium tanımlandı!\n📅 Yeni Bitiş Tarihi: {expiry}", parse_mode="Markdown")
        except: pass
    except Exception as e: bot.reply_to(message, f"❌ Hata: {e}")

@bot.message_handler(commands=['ultra_yap'])
def cmd_ultra(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    try:
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, "❌ Kullanım: `/ultra_yap <USER_ID> <GÜN>`", parse_mode="Markdown")
            return
        target_id, days = args[1], int(args[2])
        expiry = db.set_ultra(target_id, days)
        bot.reply_to(message, f"💎 **{target_id}** kullanıcısı **ULTRA** pakete geçirildi.\n📅 Bitiş: {expiry}")
        try: bot.send_message(target_id, f"💎 **Tebrikler!** Hesabınız **ULTRA** pakete yükseltildi!\n\nArtık siteleriniz TEMİZ olsa bile her 30 dakikada bir **Ekran Görüntülü Rapor** alacaksınız.", parse_mode="Markdown")
        except: pass
    except Exception as e: bot.reply_to(message, f"❌ Hata: {e}")

@bot.message_handler(commands=['ultra_foto'])
def cmd_toggle_ultra_ss_global(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    try:
        new_val = db.toggle_setting("ultra_screenshots")
        status_text = "✅ **AKTİF**" if new_val else "❌ **PASİF**"
        bot.reply_to(message, f"📸 **Global Ultra Foto Modu:** {status_text}\n(Tüm kullanıcılar için)", parse_mode="Markdown")
    except Exception as e: bot.reply_to(message, f"❌ Hata: {e}")

# --- WEBHOOK CALLBACKS (RECURSION FIXED) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("wh_"))
def handle_webhook_callbacks(call):
    if str(call.message.chat.id) != str(ADMIN_ID): return
    
    cid = call.message.chat.id
    mid = call.message.message_id
    data = call.data

    try:
        if data == "wh_list":
            _show_webhook_list(cid, mid)

        elif data == "wh_add_new":
            bot.send_message(cid, "Komut: `/webhook_ekle <isim> <url> <domainler> <gün>`", parse_mode="Markdown")

        elif data.startswith("wh_detail_"):
            wid = int(data.split("_")[-1])
            wh = db.get_webhook(wid)
            if not wh: 
                bot.answer_callback_query(call.id, "Bulunamadı")
                return
            
            status = "✅ Aktif" if wh['active'] else "❌ Pasif"
            domains_disp = "TÜMÜ (*)" if "*" in wh['domains'] else f"{len(wh['domains'])} Adet"
            
            text = (f"⚙️ **Webhook Detayı**\n🏷 İsim: {wh['name']}\n🔗 URL: `{wh['url'][:40]}...`\n"
                    f"🌐 Siteler: {domains_disp}\n📅 Bitiş: {wh['expiry_date'][:10]}\n📊 Durum: {status}")
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            toggle_txt = "Durdur ⏸️" if wh['active'] else "Başlat ▶️"
            markup.add(types.InlineKeyboardButton(toggle_txt, callback_data=f"wh_toggle_{wid}"),
                       types.InlineKeyboardButton("🗑️ Sil", callback_data=f"wh_ask_del_{wid}"))
            markup.add(types.InlineKeyboardButton("🔙 Listeye Dön", callback_data="wh_list"))
            bot.edit_message_text(text, cid, mid, reply_markup=markup, parse_mode="Markdown")

        elif data.startswith("wh_toggle_"):
            wid = int(data.split("_")[-1])
            db.toggle_webhook(wid)
            bot.answer_callback_query(call.id, "Durum Değişti")
            # Kendini çağırmak yerine datayı değiştirip tekrar işle
            call.data = f"wh_detail_{wid}"
            handle_webhook_callbacks(call)

        elif data.startswith("wh_ask_del_"):
            wid = int(data.split("_")[-1])
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(types.InlineKeyboardButton("✅ Evet Sil", callback_data=f"wh_conf_del_{wid}"),
                       types.InlineKeyboardButton("❌ İptal", callback_data=f"wh_detail_{wid}"))
            bot.edit_message_text("⚠️ **Silmek istediğinize emin misiniz?**", cid, mid, reply_markup=markup, parse_mode="Markdown")

        elif data.startswith("wh_conf_del_"):
            wid = int(data.split("_")[-1])
            db.delete_webhook(wid)
            bot.answer_callback_query(call.id, "Silindi")
            _show_webhook_list(cid, mid)

    except Exception as e:
        print(f"WH Callback Error: {e}")
        bot.answer_callback_query(call.id, "Hata oluştu")

# --- GENEL CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    cid = call.message.chat.id
    data = call.data
    import scan_engine
    
    try:
        if data == "main_menu":
            try: bot.edit_message_text("📋 **Ana Menü:**", cid, call.message.message_id, reply_markup=tg_conf.create_main_menu(), parse_mode="Markdown")
            except: pass

        elif data == "trial_start_now":
            succ, st, ex = db.register_user_scheduled(cid, False)
            if succ: 
                msg = tg_conf.MESSAGES["trial_started_now"].format(start_date=st.strftime("%d.%m.%Y %H:%M"), expiry_date=ex.strftime("%d.%m.%Y %H:%M"))
                try: bot.edit_message_text(msg, cid, call.message.message_id, reply_markup=tg_conf.create_main_menu(), parse_mode="Markdown")
                except: pass
            else:
                bot.answer_callback_query(call.id, "Zaten kayıtlısınız!", show_alert=True)

        elif data == "trial_start_monday":
            succ, st, ex = db.register_user_scheduled(cid, True)
            if succ:
                msg = tg_conf.MESSAGES["trial_scheduled_monday"].format(monday_date=st.strftime("%d.%m.%Y"), expiry_date=ex.strftime("%d.%m.%Y %H:%M"))
                try: bot.edit_message_text(msg, cid, call.message.message_id, reply_markup=tg_conf.create_main_menu(), parse_mode="Markdown")
                except: pass
            else:
                bot.answer_callback_query(call.id, "Zaten kayıtlısınız!", show_alert=True)
        
        elif data == "hesabim":
            _show_account_menu(cid, call.message, is_edit=True)

        elif data == "toggle_ultra_mode":
            new_status = db.toggle_user_ultra(cid)
            status_text = "AÇILDI" if new_status else "KAPATILDI"
            bot.answer_callback_query(call.id, f"Ultra Fotoğraf Modu {status_text}")
            _show_account_menu(cid, call.message, is_edit=True)

        elif data == "listem" or data == "refresh_list":
            domains = db.get_user_domains(cid)
            if not domains:
                bot.answer_callback_query(call.id, "Listeniz boş!")
                try: bot.edit_message_text(tg_conf.MESSAGES["list_empty"], cid, call.message.message_id, reply_markup=tg_conf.create_main_menu(), parse_mode="Markdown")
                except: pass
                return
            info = [(d, *db.get_domain_info(d)) for d in domains]
            try: bot.edit_message_text("📄 **Domainleriniz:**", cid, call.message.message_id, reply_markup=tg_conf.create_domain_list_menu(info), parse_mode="Markdown")
            except: pass
        
        elif data == "ekle":
            user_adding_domain.add(cid)
            bot.send_message(cid, tg_conf.MESSAGES["add_prompt"], parse_mode="Markdown")
            bot.answer_callback_query(call.id)

        elif data == "sil_menu":
            doms = db.get_user_domains(cid)
            if not doms:
                bot.answer_callback_query(call.id, "Listeniz boş!")
                return
            try: bot.edit_message_text("🗑️ **Silinecek domaini seçin:**", cid, call.message.message_id, reply_markup=tg_conf.create_delete_menu(doms), parse_mode="Markdown")
            except: pass

        elif data.startswith("del_confirm_"):
            dom = data.replace("del_confirm_", "")
            db.sil_domain(cid, dom)
            bot.answer_callback_query(call.id, "Silindi.")
            call.data = "listem"
            handle_callback(call)

        elif data == "sorgu":
            cmd_query(call.message)

        elif data == "sss":
            cmd_faq(call.message)

        elif data.startswith("manage_"):
            dom = data.replace("manage_", "")
            status, last_check = db.get_domain_info(dom)
            u = db.get_user_data(cid)
            is_prem = u.get("plan") in ["premium", "admin", "ultra"]
            msg = f"🌐 **{dom}**\n💡 Durum: {status}\n🕒 Son Kontrol: {last_check}"
            try: bot.edit_message_text(msg, cid, call.message.message_id, reply_markup=tg_conf.create_domain_manage_menu(dom, is_prem), parse_mode="Markdown")
            except: pass

        elif data.startswith("scan_"):
            dom = data.replace("scan_", "")
            bot.answer_callback_query(call.id, "Tarama başladı...")
            scan_engine.start_manual_scan(cid, [dom])

    except Exception as e:
        if "message is not modified" not in str(e):
            print(f"Callback Hata: {e}")
        try: bot.answer_callback_query(call.id)
        except: pass

@bot.message_handler(func=lambda m: True)
def handle_text(m):
    cid = m.chat.id
    if cid in user_adding_domain:
        u = db.get_user_data(cid)
        plan = u.get("plan")
        limit = 100 if plan == "ultra" else (50 if plan in ["premium", "admin"] else 2)
        cur = len(db.get_user_domains(cid))
        added = []
        potential_domains = m.text.replace(',', ' ').split()
        for d in potential_domains:
            clean_d = d.strip().lower()
            if len(clean_d) > 3 and "." in clean_d and not clean_d.startswith("/"):
                if cur < limit:
                    if db.ekle_domain(cid, clean_d): added.append(clean_d); cur += 1
        user_adding_domain.discard(cid)
        if added:
            import scan_engine
            msg = f"✅ **{len(added)}** domain başarıyla eklendi.\n" + "\n".join([f"• {d}" for d in added])
            bot.reply_to(m, msg, parse_mode="Markdown", reply_markup=tg_conf.create_main_menu())
            scan_engine.start_manual_scan(cid, added)
        else:
            bot.reply_to(m, "⚠️ Ekleme yapılamadı.", reply_markup=tg_conf.create_main_menu())
