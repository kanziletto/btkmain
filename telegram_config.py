from telebot import types

# --- KİMLİK VE BAĞLANTILAR ---
BOT_TOKEN = "8280880523:AAHa1jdL_JKZa1YqLr063Qp6VGOLFU2W7QQ"
ADMIN_ID = 7107697888
ADMIN_CHANNEL_ID = -1003498419781
SUPPORT_URL = "https://t.me/londonlondon25"

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
        "**Önerimiz:** Pazartesi sabahı başlatın, böylece 48 saati boşa harcamazsınız.\n\n"
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
        "❓ **Sıkça Sorulan Sorular**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "**🤖 Bot Ne İş Yapar?**\n"
        "BTK'nın (Bilgi Teknolojileri Kurumu) TİB engelleme sistemini 7/24 otomatik takip eder. "
        "Domainleriniz engellendiği anda anında bildirim alırsınız ve yeni domain'e otomatik geçiş yapılır.\n\n"
        
        "**📊 Paket Karşılaştırması:**\n\n"
        
        "🆓 **TRIAL (Deneme)**\n"
        "• Süre: 48 saat\n"
        "• Domain Limiti: 2 adet\n"
        "• Otomatik Tarama: ✅ (5 dk'da bir)\n"
        "• Anlık Bildirim: ✅\n"
        "• Oto Domain Atlama: ✅\n"
        "• Hızlı Sorgu: ❌\n"
        "• Kanıt Ekran Görüntüsü: ❌\n\n"
        
        "💎 **PREMIUM**\n"
        "• Süre: Paket süresine göre\n"
        "• Domain Limiti: 50 adet\n"
        "• Otomatik Tarama: ✅ (5 dk'da bir)\n"
        "• Anlık Bildirim: ✅\n"
        "• Oto Domain Atlama: ✅\n"
        "• Hızlı Sorgu: ✅ (Manuel tarama)\n"
        "• Kanıt Ekran Görüntüsü: ✅\n"
        "• Öncelikli Destek: ✅\n\n"
        
        "**⏰ Tarama Saatleri:**\n"
        "• Hafta İçi: 08:00 - 21:30 (5 dakikada bir)\n"
        "• Hafta Sonu: 08:00 - 21:30 (30 dakikada bir)\n"
        "• Gece: Uyku modu (BTK gece engel atmıyor)\n\n"
        
        "**🔄 Oto-Atlama Nasıl Çalışır?**\n"
        "Domain'inizde sayı varsa (örn: bet412.com) engellendiğinde "
        "bot otomatik olarak sayıyı 1 artırır (bet413.com) ve yeni domain'i takibe alır.\n\n"
        
        "**📸 Kanıt Fotoğrafı Nedir?**\n"
        "Premium üyelerde domain engelli olduğunda BTK sitesinin "
        "ekran görüntüsü kanıt olarak size iletilir.\n\n"
        
        "**🚀 Hızlı Sorgu Nedir?**\n"
        "Premium üyeler '/sorgu' komutuyla tüm domainlerini anında "
        "tarayıp sonuç alabilir. Normal taramayı beklemeden!\n\n"
        
        "**🔒 Verilerim Güvende Mi?**\n"
        "Evet! Sadece domain adlarınız kaydedilir, hiçbir kişisel veri "
        "veya site şifresi istenmez. Veriler şifreli SQLite veritabanında saklanır.\n\n"
        
        "**💰 Ödeme ve Paket Bilgisi:**\n"
        "Paket fiyatları ve satın alma için:\n"
        "👉 /destek komutuyla iletişime geçin\n\n"
        
        "**❓ Başka Sorularınız İçin:**\n"
        "📞 /destek - Canlı destek\n"
        "📋 /hesabim - Paket bilgileriniz\n"
        "📄 /listem - Domain listeniz"
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

def create_settings_menu(s_silent, s_auto, s_active):
    markup = types.InlineKeyboardMarkup(row_width=1)
    txt_silent = "✅ Açık" if s_silent else "❌ Kapalı"
    txt_auto = "✅ Açık" if s_auto else "❌ Kapalı"
    txt_active = "✅ AKTİF" if s_active else "🛑 DURDURULDU"
    
    btn1 = types.InlineKeyboardButton(f"🔔 Sessiz Mod: {txt_silent}", callback_data="toggle_silent")
    btn2 = types.InlineKeyboardButton(f"🔄 Oto-Geçiş: {txt_auto}", callback_data="toggle_auto")
    btn3 = types.InlineKeyboardButton(f"🤖 Sistem: {txt_active}", callback_data="toggle_active")
    btn_back = types.InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")
    markup.add(btn1, btn2, btn3, btn_back)
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
