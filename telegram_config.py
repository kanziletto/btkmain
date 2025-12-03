from telebot import types
from config import BOT_TOKEN, ADMIN_ID, ADMIN_CHANNEL_ID, SUPPORT_URL

# --- KOMUT LİSTESİ ---
BOT_COMMANDS = [
    types.BotCommand("start", "🚀 Botu başlat"),
    types.BotCommand("menu", "📋 Ana menü"),
    types.BotCommand("hesabim", "👤 Hesap bilgileri"),
    types.BotCommand("listem", "📄 Takip edilen domainler"),
    types.BotCommand("ekle", "➕ Domain ekle"),
    types.BotCommand("sil", "🗑️ Domain sil"),
    types.BotCommand("sorgu", "🔍 Hızlı sorgu (Premium)"),
    types.BotCommand("sss", "❓ Sık sorulan sorular"),
    types.BotCommand("webhooks", "🔗 Webhook yönetimi (Admin)"),
    types.BotCommand("webhook_ekle", "➕ Yeni Webhook (Admin)"),
    types.BotCommand("db_export", "📊 Veritabanı export (Admin)"),
    types.BotCommand("destek", "💬 Destek ve iletişim")
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
    "trial_expired": "⏳ **Deneme Süreniz Sona Erdi!**\n\nDomain takibiniz durduruldu. Kesintisiz hizmet için lütfen iletişime geçin.",
    "only_admin": "⛔ Bu komutu sadece yöneticiler kullanabilir.",
    "only_premium": "💎 Bu özellik Premium üyelere özeldir. Satın almak için destekle iletişime geçin.",
    
    "faq": (
        "🤖 **BTK Takip Botu - Detaylı Bilgi & SSS**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "**🎯 Bot Ne İşe Yarar?**\n"
        "Domainlerinizin BTK (TİB) tarafından engellenip engellenmediğini 7/24 otomatik olarak denetler. "
        "Engelleme anında Telegram ve (varsa) Slack/Discord üzerinden **kanıt fotoğraflı** bildirim gönderir.\n\n"
        
        "**⚡ Özellikler ve Çalışma Prensibi**\n\n"
        
        "**1. Akıllı Tarama Sistemi**\n"
        "• **Hafta İçi:** Her 5 dakikada bir tarama yapılır.\n"
        "• **Hafta Sonu:** BTK çalışma düzenine göre 30 dakikada bir kontrol edilir.\n"
        "• **OCR Teknolojisi:** Sorgu ekranındaki güvenlik kodları (Captcha) yapay zeka ile otomatik çözülür.\n\n"
        
        "**2. 🔄 Oto-Domain Geçişi (Auto-Switch)**\n"
        "• Siteniz engellendiğinde (Örn: `site412.com`), bot bunu algılar.\n"
        "• Domaindeki sayıyı otomatik 1 artırır (Örn: `site413.com`).\n"
        "• Yeni domaini otomatik takibe alır, eskisini siler.\n"
        "• **Not:** Domaininizde sayı yoksa bu özellik çalışmaz.\n\n"
        
        "**3. 📸 Kanıtlı Bildirimler**\n"
        "• Engelleme tespit edildiğinde BTK sayfasının ekran görüntüsü alınır.\n"
        "• Bu görsel size Telegram ve Webhook (Slack) üzerinden iletilir.\n\n"
        
        "**📦 Üyelik Paketleri**\n\n"
        "🆓 **TRIAL (Deneme)**\n"
        "• Süre: 48 Saat\n"
        "• Limit: 2 Domain\n"
        "• Özellikler: Tam Otomatik Tarama + Bildirim\n\n"
        
        "💎 **PREMIUM**\n"
        "• Süre: Paket Süresince\n"
        "• Limit: 50 Domain\n"
        "• Özellikler: Hızlı Tarama + `/sorgu` ile Anlık Manuel Kontrol + Öncelikli Destek\n\n"
        
        "**❓ Sıkça Sorulan Sorular**\n\n"
        "**S: HATA uyarısı alıyorum?**\n"
        "C: BTK sitesi bazen yoğun olabilir veya Captcha çözülemeyebilir. Sistem otomatik olarak tekrar deneyecektir.\n\n"
        "**S: Webhook nasıl eklerim?**\n"
        "C: Webhook entegrasyonu (Slack/Discord) için yönetici ile iletişime geçiniz.\n\n"
        "**💬 İletişim & Destek:**\n"
        "👉 /destek komutunu kullanabilirsiniz."
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
    "report_body": "{header}\n🌍 `{domain}`\n💡 Durum: *{status}*"
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
    btn_sil = types.InlineKeyboardButton("➖ Sil", callback_data="sil_menu")
    btn_sorgu = types.InlineKeyboardButton("🔍 Hızlı Sorgu", callback_data="sorgu")
    btn_sss = types.InlineKeyboardButton("❓ S.S.S", callback_data="sss")
    btn_destek = types.InlineKeyboardButton("💬 Destek / Satın Al", url=SUPPORT_URL)
    
    markup.add(btn_hesap, btn_liste)
    markup.add(btn_ekle, btn_sil)
    markup.add(btn_sorgu, btn_sss)
    markup.add(btn_destek)
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
