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
    
def _update_username_middleware(message):
    """Her etkileşimde username günceller"""
    try:
        if hasattr(message, 'from_user') and message.from_user:
             uid = message.from_user.id
             uname = message.from_user.username
             if uname: db.update_username(uid, uname)
    except: pass

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
    import datetime
    try:
        webhooks = db.get_webhooks(ADMIN_ID)
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        if not webhooks:
            text = "📂 **Webhook Listesi**\n\nHenüz ekli bir webhook yok."
        else:
            text = "📂 **Webhook Listesi**\nDüzenlemek için seçiniz:"
            now = datetime.datetime.now()
            for wh in webhooks:
                # Süre kontrolü
                try:
                    expiry = datetime.datetime.strptime(wh["expiry_date"][:19], "%Y-%m-%d %H:%M:%S")
                    is_expired = expiry < now
                except:
                    is_expired = False
                
                if is_expired:
                    status_icon = "⏰"  # Süresi dolmuş
                    status_text = " (Süresi Doldu)"
                elif wh["active"]:
                    status_icon = "🟢"
                    status_text = ""
                else:
                    status_icon = "🔴"
                    status_text = ""
                
                domain_count = len(wh['domains'])
                btn_text = f"{status_icon} {wh['name']} ({domain_count} Domain){status_text}"
                markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"wh_detail_{wh['id']}"))
        
        markup.add(types.InlineKeyboardButton("➕ Yeni Webhook Ekle", callback_data="wh_add_new"))
        
        if message_id:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Hata: {e}")

# --- KULLANICI KOMUTLARI ---

    # Middleware çalıştır
    _update_username_middleware(message)
    
@bot.message_handler(commands=['start'])
def cmd_start(message):
    cid = message.chat.id
    name = message.from_user.first_name
    username = message.from_user.username
    
    # --- GRUP KISITLAMASI & YÖNLENDİRME ---
    if message.chat.type in ['group', 'supergroup']:
        try:
            bot_username = bot.get_me().username
        except:
            bot_username = "BTKSorguBot"
            
        markup = types.InlineKeyboardMarkup()
        btn_start = types.InlineKeyboardButton("🤖 Botu Başlat", url=f"https://t.me/{bot_username}?start=start")
        btn_site = types.InlineKeyboardButton("🌐 Web Sitemiz", url="https://btksorgu.net")
        markup.add(btn_start, btn_site)
        
        msg = (
            "⚠️ **Grup Kurulumu Sadece Premium!**\n\n"
            "Bu botu gruplarda kullanabilmek için **Premium** paket sahibi olmalısınız.\n\n"
            "1️⃣ Özelden botu başlatın ve paket alın.\n"
            "2️⃣ `/anahtar` komutu ile bir anahtar oluşturun.\n"
            "3️⃣ Bu gruba dönüp `/bagla [ANAHTAR]` yazın."
        )
        bot.send_message(cid, msg, reply_markup=markup, parse_mode="Markdown")
        return
    # --------------------------------------
    
    # Username kaydet
    if username: db.update_username(cid, username)
    
    # Referans kontrolü (/start ref_123456)
    referrer_id = None
    if message.text and len(message.text.split()) > 1:
        param = message.text.split()[1]
        if param.startswith("ref_"):
            referrer_id = param.replace("ref_", "")
    
    conn = db._get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (str(cid),))
    existing = c.fetchone()
    conn.close()
    
    if existing:
        # Süre dolmuş mu kontrol et
        access_status = db.check_user_access(cid)
        if not access_status["access"]:
            # Süresi dolmuş - kısıtlı menü göster
            msg = tg_conf.MESSAGES["expiry_ended"]
            bot.send_message(cid, msg, reply_markup=tg_conf.create_expired_menu(), parse_mode="Markdown")
        else:
            bot.send_message(cid, tg_conf.MESSAGES["welcome_old"].format(name=name), reply_markup=tg_conf.create_main_menu())
    else:
        # Referans kaydı (varsa)
        if referrer_id and referrer_id != str(cid):
            if db.add_referral(referrer_id, cid):
                bot.send_message(cid, "🎁 **Referans Bonusu!**\nBir kullanıcı tarafından davet edildiniz.\nTrial süreniz **72 saate** uzatıldı!", parse_mode="Markdown")
                
                # Davet edene anında +24 saat bonus ver
                if db.give_immediate_referral_bonus(referrer_id, bonus_hours=24):
                    try:
                        bot.send_message(referrer_id, 
                            "🎁 **Referans Bonusu!**\n\n"
                            "Davet linkinizle birisi katıldı!\n"
                            "📅 **+24 saat** süre eklendi.\n\n"
                            "💡 Ödeme yaparsa ekstra **+7 gün** kazanırsınız!",
                            parse_mode="Markdown"
                        )
                    except: pass
        
        # Hafta sonu kontrolü
        is_weekend = datetime.datetime.now().weekday() >= 5
        
        if is_weekend:
            bot.send_message(cid, tg_conf.MESSAGES["welcome_new"].format(name=name), 
                             parse_mode="Markdown", reply_markup=tg_conf.create_trial_choice_menu(is_weekend))
        else:
            # Hafta içi direkt başlat
            # Referans ile geldiyse 72 saat, normal ise 48 saat
            trial_hours = 72 if referrer_id else 48
            succ, st, ex = db.register_user_scheduled(cid, False, username=username)
            
            # Referans bonusu için süre uzat
            if succ and referrer_id:
                db._get_conn().execute(
                    "UPDATE users SET expiry_date = ? WHERE user_id = ?",
                    (str(st + datetime.timedelta(hours=trial_hours)), str(cid))
                )
                ex = st + datetime.timedelta(hours=trial_hours)
            
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

@bot.message_handler(commands=['anahtar'])
@check_access
def cmd_key(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Kullanım: `/anahtar [domain]`\nÖrnek: `/anahtar ornek.com`")
        return
    
    domain = args[1].lower().replace('http://', '').replace('https://', '').replace('www.', '').strip()
    cid = message.chat.id
    
    # Domain bu kullanıcıya mı ait?
    owned_domains = db.get_user_domains(cid)
    if domain not in owned_domains:
        bot.reply_to(message, "❌ Bu domain listenizde bulunmuyor.")
        return
        
    # Anahtar oluştur
    key = db.create_notification_key(cid, domain)
    bot.reply_to(message, f"🔑 **Bildirim Anahtarı Oluşturuldu!**\n\nDomain: `{domain}`\nAnahtar: `{key}`\n\nBu anahtarı grubunuza eklemek için grubunuzda şunu yazın:\n`/bagla {key}`", parse_mode="Markdown")

@bot.message_handler(commands=['bagla'])
def cmd_link(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Kullanım: `/bagla [ANAHTAR]`\nÖrnek: `/bagla KEY-1234ABCD`")
        return
    
    key = args[1].strip()
    chat_id = message.chat.id
    
    # Gruba bağla
    result = db.link_chat_to_key(key, chat_id)
    
    if result["success"]:
        bot.reply_to(message, f"✅ **Başarılı!**\nBu sohbet artık **{result['domain']}** domaini için bildirim alacak.", parse_mode="Markdown")
    else:
        bot.reply_to(message, result["msg"])



@bot.message_handler(commands=['listem'])
def cmd_list(message):
    cid = message.chat.id
    
    # 1. GRUP İÇİN ÖZEL MANTIK
    if message.chat.type in ['group', 'supergroup']:
        domains = db.get_linked_domains_for_chat(cid)
        if not domains:
             bot.reply_to(message, "⚠️ **Liste Boş!**\n\nBu gruba henüz bir domain bağlanmamış.\nBağlamak için özelden anahtar alıp `/bagla` komutunu kullanın.", parse_mode="Markdown")
             return
        
        info = [(d, *db.get_domain_info(d)) for d in domains]
        bot.send_message(cid, f"🔗 **Grup Takip Listesi** ({len(domains)} Domain)", parse_mode="Markdown", reply_markup=tg_conf.create_domain_list_menu(info))
        return

    # 2. ŞAHSİ KULLANIM İÇİN (Mevcut Mantık)
    # check_access decorator yerine manuel kontrol yapıyoruz
    status = db.check_user_access(cid)
    if not status["registered"] or not status["access"]:
         # Yetkisiz veya süresi dolmuş
         if status.get("reason") == "expired":
              bot.send_message(cid, tg_conf.MESSAGES["expiry_ended"], reply_markup=tg_conf.create_expired_menu())
         else:
              # Hiç kayıtlı değilse yönlendir
              bot.send_message(cid, "⛔ Kaydınız bulunamadı. `/start` yazarak başlayın.")
         return

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

@bot.message_handler(commands=['referans', 'ref', 'davet'])
def cmd_referans(message):
    """Referans sistemi - kullanıcının referans linkini ve istatistiklerini gösterir"""
    cid = message.chat.id
    
    # Bot kullanıcı adını al
    try:
        bot_info = bot.get_me()
        bot_username = bot_info.username
    except:
        bot_username = "BTKBot"
    
    # Referans linki
    ref_link = f"https://t.me/{bot_username}?start=ref_{cid}"
    
    # İstatistikler
    stats = db.get_referral_stats(cid)
    
    text = (
        "🎁 **Referans Programı**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 **İstatistikleriniz:**\n"
        f"├ Davet Ettiğiniz: {stats['total_referrals']} kişi\n"
        f"├ Ödeme Yapan: {stats['completed']} kişi\n"
        f"├ Bekleyen: {stats['pending']} kişi\n"
        f"└ Kazanılan Süre: **+{stats['total_bonus_days']} gün**\n\n"
        "🔗 **Referans Linkiniz:**\n"
        f"`{ref_link}`\n\n"
        "📌 **Nasıl Çalışır?**\n"
        "• Birisi linkinizle katılır → **+24 saat** trial\n"
        "• Ödeme yaparsa → Size **+7 gün** bonus!"
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📤 Linki Paylaş", url=f"https://t.me/share/url?url={ref_link}&text=BTK%20Takip%20Botu%20-%20Domainlerini%20anlik%20takip%20et!"))
    markup.add(types.InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu"))
    
    bot.send_message(cid, text, parse_mode="Markdown", reply_markup=markup)

# --- SATIN ALMA SİSTEMİ ---

@bot.message_handler(commands=['satin_al', 'buy', 'premium'])
def cmd_buy(message):
    """Paket satın alma menüsü - Tek paket, süre seçimi"""
    from config import SUBSCRIPTION_DURATIONS
    
    cid = message.chat.id
    
    text = (
        "💎 **BTK İzleme Hizmeti**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📊 **Özellikler:**\n"
        "• Anlık tarama\n"
        "• Anlık Telegram bildirimleri\n"
        "• Manuel sorgu\n"
        "• 6+ ay pakette: Slack/Teams entegrasyon\n\n"
        "👇 **Süre seçin:**\n\n"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for key, dur in SUBSCRIPTION_DURATIONS.items():
        # Entegrasyon bilgisi
        integration_info = " + 🔗 Entegrasyon" if "integration" in dur["features"] else ""
        
        btn_text = f"💰 {dur['label']} - ${dur['price']} ({dur['domains']} Domain){integration_info}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"buy_{key}"))
        
        # Aylık fiyat hesapla
        monthly = round(dur["price"] / (dur["days"] / 30))
        text += f"**{dur['label']}** - ${dur['price']} (${monthly}/ay)\n"
        text += f"├ 📊 {dur['domains']} Domain\n"
        if "integration" in dur["features"]:
            text += f"└ 🔗 Slack/Teams entegrasyon\n\n"
        else:
            text += f"└ 🔔 Bildirimler\n\n"
    
    markup.add(types.InlineKeyboardButton("💬 Farklı Coin ile Ödeme", url=tg_conf.SUPPORT_URL))
    markup.add(types.InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu"))
    
    bot.send_message(cid, text, parse_mode="Markdown", reply_markup=markup)

# --- TxID DOĞRULAMA HANDLER ---

@bot.message_handler(func=lambda m: m.text and len(m.text) == 64 and all(c in '0123456789abcdefABCDEF' for c in m.text))
def handle_txid(message):
    """TxID formatındaki mesajları yakala ve doğrula"""
    from crypto_payment import verify_txid
    
    cid = message.chat.id
    txid = message.text.strip()
    
    # Bekleyen ödeme var mı?
    pending = db.get_pending_payment(str(cid))
    
    if not pending:
        bot.reply_to(message, "⚠️ Bekleyen ödeme bulunamadı.\n\nÖnce /satin_al ile paket seçin.")
        return
    
    bot.reply_to(message, "🔍 TxID doğrulanıyor, lütfen bekleyin...")
    
    # TxID'yi doğrula
    result = verify_txid(txid, pending["amount"])
    
    if result["valid"]:
        # Ödemeyi onayla
        confirm_result = db.confirm_payment(pending["invoice_id"])
        
        if confirm_result["success"]:
            text = (
                f"🎉 **Ödeme Başarılı!**\n\n"
                f"📦 Paket: **{confirm_result['plan'].upper()}**\n"
                f"📅 Bitiş: {confirm_result['new_expiry'][:10]}\n"
                f"💰 Tutar: ${result['amount']}\n"
                f"🔗 TxID: `{txid[:16]}...`\n\n"
                f"Hemen domain eklemeye başlayabilirsiniz! 👇"
            )
            bot.send_message(cid, text, parse_mode="Markdown", reply_markup=tg_conf.create_main_menu())
            
            # Admin'e bildir
            admin_msg = (
                f"💰 **Yeni Ödeme (TxID Onaylı)!**\n"
                f"User: `{cid}`\n"
                f"Plan: {confirm_result['plan']}\n"
                f"Tutar: ${result['amount']}\n"
                f"TxID: `{txid[:24]}...`"
            )
            try: bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
            except: pass
            
            # Referans ödülü işle
            ref_result = db.process_referral_reward(str(cid), bonus_days=7)
            if ref_result["success"]:
                referrer_id = ref_result["referrer_id"]
                try:
                    ref_msg = (
                        f"🎁 **Referans Ödülü!**\n\n"
                        f"Davet ettiğiniz kullanıcı ödeme yaptı!\n"
                        f"📅 **+7 gün** bonus süre eklendi."
                    )
                    bot.send_message(referrer_id, ref_msg, parse_mode="Markdown")
                except: pass
        else:
            bot.send_message(cid, f"❌ Hata: {confirm_result.get('error', 'Bilinmiyor')}")
    else:
        # Doğrulama başarısız
        error_msg = result.get("error", "Bilinmeyen hata")
        bot.send_message(cid, f"❌ **Doğrulama Başarısız**\n\n{error_msg}", parse_mode="Markdown")

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

@bot.message_handler(commands=['odeme_onayla'])
def cmd_confirm_payment(message):
    """Admin: Bekleyen ödemeyi onayla - /odeme_onayla <USER_ID>"""
    if str(message.chat.id) != str(ADMIN_ID): return
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "❌ Kullanım: `/odeme_onayla <USER_ID>`", parse_mode="Markdown")
            return
        
        target_id = args[1]
        
        # Bekleyen ödemeyi bul
        pending = db.get_pending_payment(target_id)
        
        if not pending:
            bot.reply_to(message, f"⚠️ `{target_id}` için bekleyen ödeme bulunamadı.", parse_mode="Markdown")
            return
        
        # Ödemeyi onayla
        result = db.confirm_payment(pending["invoice_id"])
        
        if result["success"]:
            bot.reply_to(message, 
                f"✅ **Ödeme Onaylandı!**\n"
                f"User: `{target_id}`\n"
                f"Plan: {result['plan']}\n"
                f"Süre: {result['days']} gün\n"
                f"Bitiş: {result['new_expiry'][:10]}", 
                parse_mode="Markdown"
            )
            
            # Kullanıcıya bildir
            try:
                user_msg = (
                    f"🎉 **Ödeme Onaylandı!**\n\n"
                    f"📦 Paket: **{result['plan'].upper()}**\n"
                    f"📅 Bitiş: {result['new_expiry'][:10]}\n\n"
                    f"Hemen domain eklemeye başlayabilirsiniz! 👇"
                )
                bot.send_message(target_id, user_msg, parse_mode="Markdown", reply_markup=tg_conf.create_main_menu())
            except: pass
        else:
            bot.reply_to(message, f"❌ Hata: {result.get('error', 'Bilinmeyen hata')}")
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {e}")

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

@bot.message_handler(commands=['kullanicilar', 'users'])
def cmd_list_users(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    try:
        users = db.get_all_users_with_details()
        if not users:
            bot.reply_to(message, "⚠️ Kayıtlı kullanıcı yok.")
            return

        text = "👥 **Kullanıcı Listesi**\n"
        text += "Format: `ID | @Username | Paket | Bitiş`\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        
        # Uzun liste kontrolü (Max 4096 karakter)
        chunk = ""
        for u in users:
            uname = f"@{u['username']}" if u['username'] else "-"
            expiry = u['expiry_date'][:10] if u['expiry_date'] else "-"
            line = f"`{u['user_id']}` | {uname} | {u['plan']} | {expiry}\n"
            
            if len(chunk) + len(line) > 3800:
                bot.send_message(message.chat.id, text + chunk, parse_mode="Markdown")
                chunk = ""
                text = "" # Sonraki mesajlar başlıksız olsun
            
            chunk += line
            
        if chunk:
            bot.send_message(message.chat.id, text + chunk, parse_mode="Markdown")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {e}")

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
            import datetime
            wid = int(data.split("_")[-1])
            wh = db.get_webhook(wid)
            if not wh: 
                bot.answer_callback_query(call.id, "Bulunamadı")
                return
            
            # Süre kontrolü
            now = datetime.datetime.now()
            try:
                expiry = datetime.datetime.strptime(wh["expiry_date"][:19], "%Y-%m-%d %H:%M:%S")
                is_expired = expiry < now
            except:
                is_expired = False
            
            if is_expired:
                status = "⏰ Süresi Doldu"
            elif wh['active']:
                status = "✅ Aktif"
            else:
                status = "❌ Pasif"
            
            # Domain listesi
            if "*" in wh['domains']:
                domains_disp = "TÜMÜ (*)"
            elif len(wh['domains']) <= 5:
                domains_disp = ", ".join(wh['domains'])
            else:
                domains_disp = ", ".join(wh['domains'][:5]) + f" +{len(wh['domains'])-5}"
            
            text = (f"⚙️ **Webhook Detayı**\n"
                    f"🏷 İsim: {wh['name']}\n"
                    f"🔗 URL: `{wh['url'][:40]}...`\n"
                    f"🌐 Siteler: {domains_disp}\n"
                    f"📅 Bitiş: {wh['expiry_date'][:10]}\n"
                    f"📊 Durum: {status}")
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            
            if is_expired:
                # Süresi dolmuş - sadece yenile butonu
                markup.add(types.InlineKeyboardButton("🔄 Süreyi Yenile", callback_data=f"wh_renew_{wid}"),
                           types.InlineKeyboardButton("🗑️ Sil", callback_data=f"wh_ask_del_{wid}"))
            else:
                toggle_txt = "Durdur ⏸️" if wh['active'] else "Başlat ▶️"
                markup.add(types.InlineKeyboardButton(toggle_txt, callback_data=f"wh_toggle_{wid}"),
                           types.InlineKeyboardButton("🗑️ Sil", callback_data=f"wh_ask_del_{wid}"))
            
            markup.add(types.InlineKeyboardButton("🔙 Listeye Dön", callback_data="wh_list"))
            bot.edit_message_text(text, cid, mid, reply_markup=markup, parse_mode="Markdown")

        elif data.startswith("wh_renew_"):
            wid = int(data.split("_")[-1])
            wh = db.get_webhook(wid)
            if wh:
                bot.answer_callback_query(call.id, "Yenileme talimatları gönderildi")
                bot.send_message(cid, 
                    f"🔄 **Webhook Yenileme**\n\n"
                    f"Webhook: `{wh['name']}`\n\n"
                    f"Yenilemek için aşağıdaki komutu kullanın:\n"
                    f"`/webhook_ekle {wh['name']} {wh['url']} {'*' if '*' in wh['domains'] else ','.join(wh['domains'])} 365`\n\n"
                    f"Ardından eski webhook'u silebilirsiniz.",
                    parse_mode="Markdown"
                )
            else:
                bot.answer_callback_query(call.id, "Bulunamadı")

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
    

    
    # GRUP İÇİN ÖZEL MANTIK (Linked Groups)
    if call.message.chat.type in ['group', 'supergroup']:
        # Sadece listeleme ile ilgili butonlara izin ver
        # Örn: list_refresh, list_page, domain_detail vs.
        ALLOWED_GROUP = ["main_menu", "refresh_list"] 
        # Domain detay butonları usually "d_example.com" formatında olabilir veya listeden gelir
        
        # Eğer buton bir "listeleme" veya "detay" butonu ise ve grup bağlıysa izin ver
        # Şimdilik basitçe: Gruplarda expiry kontrolünü atla, ama sadece belirli butonlara izin ver
        
        # Grubun bağlı domaini var mı?
        linked_domains = db.get_linked_domains_for_chat(cid)
        if not linked_domains:
             bot.answer_callback_query(call.id, "⚠️ Bu gruba bağlı domain yok.", show_alert=True)
             return

        # Sadece listeleme ve refresh serbest, diğerleri (ekle, sil, ödeme) yasak
        if data in ["add_new", "buy_menu", "account", "support"]:
             bot.answer_callback_query(call.id, "⚠️ Bu işlem sadece özel mesajda yapılabilir.", show_alert=True)
             return
             
        # Expiry kontrolünü atla (Sonsuz izin, çünkü sahibi zaten ödüyor)
        is_expired = False
        
    else:
        # ŞAHSİ KULLANIM İÇİN NORMAL KONTROL
        ALLOWED_FOR_EXPIRED = ["satin_al", "sss", "back_to_expiry"]
        access_status = db.check_user_access(cid)
        is_expired = not access_status["access"]
    

    
    if is_expired:
        # buy_ ile başlayanlar da izinli
        is_allowed = data in ALLOWED_FOR_EXPIRED or data.startswith("buy_")
        if not is_allowed:
            # İzinsiz callback - expiry mesajı göster
            msg = tg_conf.MESSAGES["expiry_ended"]
            markup = tg_conf.create_expired_menu()
            try: 
                bot.edit_message_text(msg, cid, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
            except: 
                bot.send_message(cid, msg, reply_markup=markup, parse_mode="Markdown")
            bot.answer_callback_query(call.id, "⛔ Üyeliğiniz sona erdi!", show_alert=True)
            return
    
    try:
        # --- PAKET TİPİ SEÇİMİ ---
        if data.startswith("tier_"):
            tier_key = data.replace("tier_", "")
            from config import SUBSCRIPTION_TIERS, SUBSCRIPTION_DURATIONS, get_plan_price
            
            tier = SUBSCRIPTION_TIERS.get(tier_key)
            if not tier:
                bot.answer_callback_query(call.id, "Geçersiz paket!", show_alert=True)
                return
            
            bot.answer_callback_query(call.id)
            
            text = (
                f"⏱️ **{tier['name']} - Süre Seçin**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📊 {tier['domains']} Domain\n\n"
            )
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            buttons = []
            
            for dur_key, dur in SUBSCRIPTION_DURATIONS.items():
                plan = get_plan_price(tier_key, dur_key)
                btn_text = f"{dur['label']} - ${plan['price']}"
                buttons.append(types.InlineKeyboardButton(btn_text, callback_data=f"buy_{tier_key}_{dur_key}"))
            
            # 2'li satırlar
            for i in range(0, len(buttons), 2):
                markup.row(*buttons[i:i+2])
            
            markup.add(types.InlineKeyboardButton("🔙 Paketler", callback_data="back_to_plans"))
            
            try:
                bot.edit_message_text(text, cid, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
            except:
                bot.send_message(cid, text, parse_mode="Markdown", reply_markup=markup)
            return
        
        elif data == "back_to_plans":
            # /satin_al menüsüne geri dön
            from config import SUBSCRIPTION_TIERS
            
            text = "💎 **Abonelik Paketleri**\n━━━━━━━━━━━━━━━━━━━━\n\n"
            markup = types.InlineKeyboardMarkup(row_width=1)
            
            for key, tier in SUBSCRIPTION_TIERS.items():
                btn_text = f"💰 {tier['name']} - ${tier['base_price']}/ay ({tier['domains']} Domain)"
                markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"tier_{key}"))
                text += f"**{tier['name']}** - ${tier['base_price']}/ay\n└ 📊 {tier['domains']} Domain\n\n"
            
            text += "👇 Paket tipini seçin:"
            markup.add(types.InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu"))
            
            try:
                bot.edit_message_text(text, cid, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
            except:
                pass
            return
        
        # --- ÖDEME BİLGİLERİ (yeni format: buy_1m, buy_3m, etc.) ---
        if data.startswith("buy_"):
            dur_key = data.replace("buy_", "")  # Sadece süre: 1m, 3m, 6m, 12m
            
            from config import get_plan_price, USDT_WALLET_ADDRESS
            from crypto_payment import get_payment_info
            import time
            
            plan = get_plan_price(dur_key)
            if not plan:
                bot.answer_callback_query(call.id, "Geçersiz süre!", show_alert=True)
                return
            
            # Süre dolmuş mu kontrol et
            access_status = db.check_user_access(cid)
            is_expired = not access_status["access"]
            
            # Cüzdan kontrolü
            if USDT_WALLET_ADDRESS == "YOUR_TRC20_WALLET_ADDRESS_HERE":
                bot.answer_callback_query(call.id, "Ödeme sistemi yapılandırılmamış!", show_alert=True)
                bot.send_message(cid, "⚠️ Ödeme sistemi henüz aktif değil.\nLütfen /destek ile iletişime geçin.")
                return
            
            bot.answer_callback_query(call.id, "Ödeme bilgileri hazırlanıyor...")
            
            # Ödeme bilgilerini al
            payment_info = get_payment_info(f"standard_{dur_key}")
            
            if payment_info:
                # Database'e kaydet
                invoice_id = f"{cid}_{int(time.time())}"
                db.create_payment(
                    str(cid), 
                    invoice_id, 
                    payment_info["amount"], 
                    "USDT", 
                    f"standard_{dur_key}", 
                    plan["days"]
                )
                
                # Webhook bilgisi
                webhook_info = "\n🔗 **Webhook:** Slack/Teams entegrasyonu dahil" if "webhook" in plan["features"] else ""
                
                text = (
                    f"💳 **Ödeme Bilgileri**\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"📦 Paket: **{plan['name']}**\n"
                    f"⏱️ Süre: {plan['days']} Gün\n"
                    f"📊 Domain: {plan['domains']} adet{webhook_info}\n\n"
                    f"💰 **Gönderilecek Tutar:**\n"
                    f"`{payment_info['amount']}` USDT\n\n"
                    f"📍 **Cüzdan Adresi (TRC20):**\n"
                    f"`{USDT_WALLET_ADDRESS}`\n\n"
                    f"✅ **Ödeme Sonrası:**\n"
                    f"Transfer **TxID**'nizi bu sohbete gönderin.\n"
                    f"Otomatik doğrulama sonrası paketiniz aktif olur."
                )
                
                markup = types.InlineKeyboardMarkup()
                # Süre dolmuşsa geri butonunda expiry mesajına dön
                if is_expired:
                    markup.add(types.InlineKeyboardButton("🔙 Geri", callback_data="satin_al"))
                else:
                    markup.add(types.InlineKeyboardButton("🔙 Geri", callback_data="satin_al"))
                
                bot.send_message(cid, text, parse_mode="Markdown", reply_markup=markup)
            else:
                bot.send_message(cid, "❌ Ödeme bilgileri oluşturulamadı.")
            return

        if data == "satin_al":
            # Satın alma menüsünü göster
            from config import SUBSCRIPTION_DURATIONS
            
            # Süre dolmuş mu kontrol et
            access_status = db.check_user_access(cid)
            is_expired = not access_status["access"]
            
            text = (
                "💎 **BTK İzleme Hizmeti**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "📊 **Özellikler:**\n"
                "• Anlık tarama\n"
                "• Anlık Telegram bildirimleri\n"
                "• Manuel sorgu\n"
                "• 6+ ay pakette: Slack/Teams entegrasyon\n\n"
                "👇 **Süre seçin:**\n"
            )
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            for key, dur in SUBSCRIPTION_DURATIONS.items():
                integration_info = " + 🔗 Entegrasyon" if "integration" in dur["features"] else ""
                btn_text = f"💰 {dur['label']} - ${dur['price']} ({dur['domains']} Domain){integration_info}"
                markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"buy_{key}"))
            
            markup.add(types.InlineKeyboardButton("💬 Farklı Coin ile Ödeme", url=tg_conf.SUPPORT_URL))
            
            # Süre dolmuşsa geri butonunda expiry mesajına dön
            if is_expired:
                markup.add(types.InlineKeyboardButton("🔙 Geri", callback_data="back_to_expiry"))
            else:
                markup.add(types.InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu"))
            
            try: bot.edit_message_text(text, cid, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
            except: bot.send_message(cid, text, parse_mode="Markdown", reply_markup=markup)
            return

        if data == "referans":
            # Bot kullanıcı adını al
            try:
                bot_info = bot.get_me()
                bot_username = bot_info.username
            except:
                bot_username = "BTKBot"
            
            # Referans linki
            ref_link = f"https://t.me/{bot_username}?start=ref_{cid}"
            
            # İstatistikler
            stats = db.get_referral_stats(cid)
            
            text = (
                "🎁 **Referans Programı**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📊 **İstatistikleriniz:**\n"
                f"├ Davet Ettiğiniz: {stats['total_referrals']} kişi\n"
                f"├ Ödeme Yapan: {stats['completed']} kişi\n"
                f"└ Kazanılan Süre: **+{stats['total_bonus_days']} gün**\n\n"
                "🔗 **Referans Linkiniz:**\n"
                f"`{ref_link}`\n\n"
                "📌 **Nasıl Çalışır?**\n"
                "• Birisi linkinizle katılır → +24 saat trial\n"
                "• Ödeme yaparsa → Size **+7 gün** bonus!"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📤 Linki Paylaş", url=f"https://t.me/share/url?url={ref_link}&text=BTK%20Takip%20Botu"))
            markup.add(types.InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu"))
            
            try: bot.edit_message_text(text, cid, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
            except: bot.send_message(cid, text, parse_mode="Markdown", reply_markup=markup)
            return

        if data == "main_menu":
            try: bot.edit_message_text("📋 **Ana Menü:**", cid, call.message.message_id, reply_markup=tg_conf.create_main_menu(), parse_mode="Markdown")
            except: pass

        elif data == "back_to_expiry":
            # Süre dolmuş kullanıcı geri butonuna tıkladığında expiry mesajı göster
            msg = tg_conf.MESSAGES["expiry_ended"]
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("💰 Satın Al", callback_data="satin_al"))
            try: bot.edit_message_text(msg, cid, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
            except: bot.send_message(cid, msg, reply_markup=markup, parse_mode="Markdown")

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
            # Domain temizleme
            clean_d = d.strip().lower()
            # Protokol kaldır
            clean_d = clean_d.replace("https://", "").replace("http://", "")
            # www. kaldır
            if clean_d.startswith("www."):
                clean_d = clean_d[4:]
            # Trailing slash ve path kaldır
            clean_d = clean_d.split("/")[0]
            
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
