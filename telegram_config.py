from telebot import types

# --- KİMLİK VE BAĞLANTILAR ---
BOT_TOKEN = "8280880523:AAHa1jdL_JKZa1YqLr063Qp6VGOLFU2W7QQ"
ADMIN_ID = 7107697888
ADMIN_CHANNEL_ID = -1003498419781
SUPPORT_URL = "https://t.me/londonlondon25"

# --- KOMUT LİSTESİ ---
BOT_COMMANDS = [
    types.BotCommand("start", "Botu başlat / Yenile"),
    types.BotCommand("menu", "Ana menüyü aç"),
    types.BotCommand("hesabim", "Üyelik ve Limit durumu"),
    types.BotCommand("listem", "Takip edilen domainler"),
    types.BotCommand("ekle", "Yeni domain ekle"),
    types.BotCommand("sil", "Domain silme menüsü"),
    types.BotCommand("sorgu", "Hızlı manuel sorgu (Premium)"),
    types.BotCommand("sss", "Sıkça Sorulan Sorular"),
    types.BotCommand("destek", "İletişim ve Destek"),
    types.BotCommand("ayarlar", "Yönetim Paneli (Admin)")
]

# --- MESAJ METİNLERİ ---
MESSAGES = {
    "welcome_new": (
        "👋 **Hoş Geldin {name}!**\n\n"
        "🤖 **TiB & BTK Takip Botu**\n"
        "Domainlerinizin engel durumunu 7/24 otomatik takip eder.\n\n"
        "🎁 **Hediye:** Sana özel **48 Saatlik Deneme Sürümü** tanımlandı!\n"
        "✅ 2 Adet Domain Ekleme\n✅ Anlık Engel Bildirimi\n✅ Otomatik Domain Atlama\n\n"
        "👇 Başlamak için aşağıdaki menüyü kullanabilirsin."
    ),
    "welcome_old": "👋 Tekrar Merhaba {name}!\nKontrol paneli hazır:",
    
    "access_denied": "⛔ **Erişim Reddedildi**\n\nDurum: {status}\n\nDevam etmek için lütfen paket satın alın.",
    "trial_expired": "⏳ **Deneme Süreniz Sona Erdi!**\n\nDomain takibiniz durduruldu. Kesintisiz hizmet için lütfen iletişime geçin.",
    "only_admin": "⛔ Bu komutu sadece yöneticiler kullanabilir.",
    "only_premium": "💎 Bu özellik Premium üyelere özeldir. Satın almak için destekle iletişime geçin.",
    
    "faq": (
        "❓ **Sıkça Sorulan Sorular**\n\n"
        "**Bot ne yapar?**\nBTK engelini takip eder.\n\n"
        "**Oto-Atlama:**\n412 -> 413 geçişini otomatik yapar.\n\n"
        "**Premium:**\n50+ Domain, Hızlı Sorgu, Kanıt Fotosu."
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
    """
    domains_info: [('site.com', 'TEMİZ', '14:30'), ...] listesi alır.
    """
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
