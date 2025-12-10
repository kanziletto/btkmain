from telebot import types
from config import BOT_TOKEN, ADMIN_ID, ADMIN_CHANNEL_ID, SUPPORT_URL

# --- KOMUT LİSTESİ ---
BOT_COMMANDS = [
    types.BotCommand("start", "🚀 Botu başlat"),
    types.BotCommand("menu", "📋 Ana menü"),
    types.BotCommand("hesabim", "👤 Hesap bilgileri"),
    types.BotCommand("listem", "📄 Takip edilen domainler"),
    types.BotCommand("ekle", "➕ Domain ekle"),
    types.BotCommand("sorgu", "🔍 Manuel sorgu"),
    types.BotCommand("satin_al", "💰 Paket satın al"),
    types.BotCommand("referans", "🎁 Davet et ve kazan"),
    types.BotCommand("sss", "❓ Sık sorulan sorular"),
    types.BotCommand("destek", "💬 Canlı destek")
]

# --- MESAJ METİNLERİ ---
MESSAGES = {
    "welcome_new": (
        "👋 **Hoş Geldin {name}!**\n\n"
        "🤖 **TiB & BTK Takip Botu**\n"
        "Domainlerinizin engel durumunu 7/24 otomatik takip eder.\n\n"
        "🎁 **48 Saatlik Ücretsiz Deneme!**\n\n"
        "⏰ **Ne Zaman Başlamak İstersiniz?**"
    ),
    
    "trial_choice_weekend": (
        "📅 **Bugün {day_name}**\n\n"
        "⚠️ BTK hafta sonu genellikle engel atmıyor!\n\n"
        "**Önerimiz:** Pazartesi sabahı başlatın.\n\n"
        "👇 Tercihinizi seçin:"
    ),
    
    "trial_choice_weekday": (
        "📅 **Bugün {day_name}**\n\n"
        "✅ Hafta içindesiniz, hemen başlayabilirsiniz!\n\n"
        "👇 Tercihinizi seçin:"
    ),
    
    "trial_started_now": (
        "🎉 **Trial Başlatıldı!**\n\n"
        "⏱️ Süre: 48 saat\n"
        "🚀 Başlangıç: {start_date}\n"
        "⏳ Bitiş: {expiry_date}\n\n"
        "✅ 2 Domain Ekleyebilirsiniz\n"
        "✅ Otomatik Tarama Aktif\n"
        "✅ Anlık Bildirimler\n"
        "✅ Oto-Domain Atlama\n\n"
        "👇 Domain eklemek için menüyü kullanın:"
    ),
    
    "trial_scheduled_monday": (
        "📅 **Trial Pazartesi Başlayacak!**\n\n"
        "🗓️ Başlangıç: **{monday_date}** (Pazartesi 08:00)\n"
        "⏳ Bitiş: **{expiry_date}** (Çarşamba 08:00)\n\n"
        "✅ Şimdiden domain ekleyebilirsiniz!\n"
        "✅ Pazartesi sabahı tarama otomatik başlar\n\n"
        "👇 Domain eklemek için menüyü kullanın:"
    ),
    
    "welcome_old": "👋 Tekrar Merhaba {name}!\nKontrol paneli hazır:",
    "access_denied": "⛔ **Erişim Reddedildi**\n\nDurum: {status}\n\nDevam etmek için lütfen paket satın alın.",
    "only_admin": "⛔ Bu komutu sadece yöneticiler kullanabilir.",
    "only_premium": "💎 Bu özellik Premium üyelere özeldir. Satın almak için destekle iletişime geçin.",
    
    "faq": (
        "🤖 **BTK Takip Botu - SSS**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "**🎯 Bot Ne İşe Yarar?**\n"
        "Domainlerinizi 7/24 otomatik kontrol eder, engelleme anında bildirir.\n\n"
        
        "**⚡ Tarama Sıklığı**\n"
        "• Hafta içi: Anlık tarama\n"
        "• Hafta sonu: 1 saatte bir\n\n"
        
        "**🔄 Oto-Geçiş**\n"
        "site110.com engellenince → site111.com otomatik eklenir.\n\n"
        
        "**📦 Paketler**\n"
        "🆓 Deneme: 48 saat, 2 domain\n\n"
        "💰 Ücretli:\n"
        "• 1 Ay - $60 (5 domain)\n"
        "• 3 Ay - $160 (10 domain)\n"
        "• 6 Ay - $300 (15 domain + Entegrasyon)\n"
        "• 12 Ay - $500 (25 domain + Entegrasyon)\n\n"
        
        "**🎁 Referans Programı**\n"
        "Arkadaşını davet et → +7 gün bonus kazan!\n"
        "/referans ile linkini al.\n\n"
        
        "**❓ Sorular**\n"
        "**HATA uyarısı?** → Sistem otomatik tekrar dener.\n"
        "**Domain formatı?** → `site.com` (https:// olmadan)"
    ),
    
    "add_prompt": "✍️ **Eklenecek domainleri yazın:**\n(Tekli, virgüllü veya .txt dosyası gönderebilirsiniz)",
    "del_prompt": "🗑️ **Silmek istediğiniz domaini seçin:**",
    "list_empty": "⚠️ Listeniz boş. 'Domain Ekle' diyerek başlayın.",
    
    "account_info": (
        "👤 **Hesap Bilgileri**\n"
        "🆔 ID: `{id}`\n"
        "📦 Paket: **{plan}**\n"
        "📊 Limit: {current} / {limit}\n"
        "📅 Bitiş: {expiry}"
    ),
    
    "report_header_change": "🚨 *DURUM DEĞİŞTİ!*",
    "report_header_banned": "🚫 *YASAKLI (SÜREKLİ)*",
    "report_body": "{header}\n🌍 `{domain}`\n💡 Durum: *{status}*",
    
    "expiry_warning_24h": (
        "⏰ **Üyelik Uyarısı**\n\n"
        "Üyeliğinizin bitmesine **24 saatten az** kaldı!\n"
        "📅 Bitiş: {expiry}\n\n"
        "Kesintisiz hizmet için şimdi yenileyin!"
    ),
    
    "expiry_ended": (
        "⛔ **Üyelik Sona Erdi**\n\n"
        "Domain takibiniz durduruldu.\n\n"
        "Devam etmek için paket satın alın:"
    )
}

# --- MENÜ TASARIMLARI (UI) ---

def create_trial_choice_menu(is_weekend):
    """Trial başlangıç seçimi menüsü"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if is_weekend:
        btn_now = types.InlineKeyboardButton("⚡ Hemen Başlat (Test İçin)", callback_data="trial_start_now")
        btn_monday = types.InlineKeyboardButton("📅 Pazartesi Başlat (ÖNERİLEN)", callback_data="trial_start_monday")
    else:
        btn_now = types.InlineKeyboardButton("⚡ Hemen Başlat", callback_data="trial_start_now")
        btn_monday = types.InlineKeyboardButton("📅 Pazartesi Başlat", callback_data="trial_start_monday")
    
    markup.add(btn_monday)
    markup.add(btn_now)
    return markup

def create_main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_hesap = types.InlineKeyboardButton("👤 Hesabım", callback_data="hesabim")
    btn_liste = types.InlineKeyboardButton("📄 Domainlerim", callback_data="listem")
    btn_ekle = types.InlineKeyboardButton("➕ Ekle", callback_data="ekle")
    btn_sorgu = types.InlineKeyboardButton("🔍 Manuel Sorgu", callback_data="sorgu")
    btn_sss = types.InlineKeyboardButton("❓ S.S.S", callback_data="sss")
    btn_referans = types.InlineKeyboardButton("🎁 Davet Et", callback_data="referans")
    btn_satin_al = types.InlineKeyboardButton("💰 Satın Al", callback_data="satin_al")
    btn_destek = types.InlineKeyboardButton("💬 Canlı Destek", url=SUPPORT_URL)
    
    markup.add(btn_hesap, btn_liste)
    markup.add(btn_ekle, btn_sorgu)
    markup.add(btn_sss, btn_referans)
    markup.add(btn_satin_al, btn_destek)
    return markup

def create_expired_menu():
    """Süresi dolmuş kullanıcılar için kısıtlı menü"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_satin_al = types.InlineKeyboardButton("💰 Satın Al", callback_data="satin_al")
    btn_sss = types.InlineKeyboardButton("❓ S.S.S", callback_data="sss")
    btn_destek = types.InlineKeyboardButton("💬 Canlı Destek", url=SUPPORT_URL)
    
    markup.add(btn_satin_al)
    markup.add(btn_sss, btn_destek)
    return markup

def create_domain_list_menu(domains_info):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for domain, status, time in domains_info:
        icon = "✅" if status == "TEMİZ" else "🚫" if status == "ENGELLİ" else "❓"
        btn_text = f"{icon} {domain} | 🕒 {time}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"manage_{domain}"))
    
    markup.add(types.InlineKeyboardButton("🔄 Durumları Güncelle", callback_data="refresh_list"))
    markup.add(types.InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu"))
    return markup

def create_domain_manage_menu(domain, is_premium):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_del = types.InlineKeyboardButton("🗑️ Sil", callback_data=f"del_confirm_{domain}")
    btn_scan = types.InlineKeyboardButton("🔍 Tara (Premium)", callback_data=f"scan_{domain}")
    btn_back = types.InlineKeyboardButton("🔙 Geri", callback_data="listem")
    
    if is_premium:
        markup.add(btn_scan, btn_del)
    else:
        markup.add(btn_del)
    markup.add(btn_back)
    return markup

def create_delete_menu(domains):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for d in domains:
        markup.add(types.InlineKeyboardButton(f"🗑️ {d} (Sil)", callback_data=f"del_confirm_{d}"))
    markup.add(types.InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu"))
    return markup
