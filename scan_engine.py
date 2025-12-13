import time
import threading
import queue
import datetime
import os
import sys
import requests
import io
from contextlib import contextmanager
from btk import BTKScanner
from database import Database
from utils import logger
import telegram_bot as tg 
import telegram_config as tg_conf
import visuals
import re
try:
    from config import IMAGE_UPLOAD_URL, MAX_CONCURRENT_SCANS, ADMIN_ID, ADMIN_CHANNEL_ID
except ImportError:
    IMAGE_UPLOAD_URL = "" 
    MAX_CONCURRENT_SCANS = 2 # Stabilite için 1 yaptık
    ADMIN_ID = 7107697888
    ADMIN_CHANNEL_ID = -1003498419781

from concurrent.futures import ThreadPoolExecutor

# --- AYARLAR ---
scanner_pool = queue.Queue(maxsize=MAX_CONCURRENT_SCANS)
db = Database()
print_lock = threading.Lock()
upload_session = requests.Session()

# ✅ BİLDİRİM KUYRUĞU
notification_queue = queue.Queue()

# ✅ AKTİF TARAMA KİLİDİ
active_user_scans = set()
scan_lock = threading.Lock()

class Colors:
    GREEN = '\033[92m'; RED = '\033[91m'; YELLOW = '\033[93m'; BLUE = '\033[94m'; RESET = '\033[0m'; BOLD = '\033[1m'

try:
    for i in range(MAX_CONCURRENT_SCANS):
        scanner_pool.put(BTKScanner())
except: pass

@contextmanager
def get_scanner():
    s = scanner_pool.get()
    try: yield s
    finally: scanner_pool.put(s)

def increment_domain(domain):
    matches = list(re.finditer(r'\d+', domain))
    if not matches: return None
    match = matches[-1]
    try:
        new = int(match.group()) + 1
        return domain[:match.start()] + str(new) + domain[match.end():]
    except: return None

def upload_image_to_remote(image_data):
    """
    Görüntüyü (Path veya BytesIO) uzak sunucuya yükler ve URL döndürür.
    """
    try:
        files = {}
        opened_file = None
        
        # Durum 1: Dosya yolu (String) ise
        if isinstance(image_data, str) and os.path.exists(image_data):
            opened_file = open(image_data, 'rb')
            files = {'file': ('evidence.png', opened_file, 'image/png')}
        
        # Durum 2: RAM verisi (BytesIO) ise
        elif isinstance(image_data, io.BytesIO):
            image_data.seek(0) # İmleci başa al
            files = {'file': ('evidence.png', image_data, 'image/png')}
            
        else:
            return None

        # Yükleme İsteği
        response = upload_session.post(IMAGE_UPLOAD_URL, files=files, timeout=30)
        
        # Dosya açıldıysa kapat
        if opened_file:
            opened_file.close()

        if response.status_code == 200:
            url = response.json().get("url")
            if url: logger.info(f"📸 Resim Yüklendi: {url}")
            return url
        return None
    except Exception as e:
        logger.error(f"Upload hatası: {e}")
        return None

# --- BİLDİRİM İŞÇİSİ ---
def notification_worker():
    while True:
        task = notification_queue.get()
        try:
            t_type = task.get("type")
            
            if t_type == "webhook":
                url = task["url"]
                payload = task["payload"]
                try:
                    # Retry Mekanizması (Basit)
                    for i in range(3):
                        try:
                            r = requests.post(url, json=payload, timeout=10)
                            if r.status_code in [200, 201, 204]:
                                print(f"✅ Webhook İletildi! (HTTP {r.status_code})")
                                break
                        except:
                            time.sleep(2)
                except Exception as e:
                    print(f"❌ Webhook Hatası: {e}")

            elif t_type == "telegram_text":
                tg.send_message(task["chat_id"], task["text"])
                
            elif t_type == "telegram_photo":
                if "data" in task:
                    data = task["data"]
                    if isinstance(data, io.BytesIO):
                        data.seek(0)
                        tg.send_photo(task["chat_id"], data, caption=task["caption"])
                    elif isinstance(data, str) and os.path.exists(data):
                        with open(data, 'rb') as f: tg.send_photo(task["chat_id"], f, caption=task["caption"])
                elif "path" in task and os.path.exists(task["path"]):
                     with open(task["path"], 'rb') as f: tg.send_photo(task["chat_id"], f, caption=task["caption"])

            elif t_type == "telegram_doc":
                 if os.path.exists(task["path"]):
                    with open(task["path"], 'rb') as f: tg.send_document(task["chat_id"], f, caption=task["caption"])
            
            elif t_type == "telegram_text_with_button":
                from telebot import types
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(task["button_text"], callback_data=task["button_callback"]))
                tg.bot.send_message(task["chat_id"], task["text"], reply_markup=markup, parse_mode="Markdown")
            
            elif t_type == "telegram_chart":
                 tg.send_photo(task["chat_id"], task["chart"], caption=task["caption"])

        except Exception as e:
            print(f"Bildirim Worker Hatası: {e}")
        finally:
            notification_queue.task_done()

threading.Thread(target=notification_worker, daemon=True, name="Notifier").start()

def queue_webhook(user_id, domain, old_status, new_status, image_url=None, next_domain=None):
    webhooks = db.get_active_webhooks_for_domain(user_id, domain)
    if not webhooks: return
    
    for webhook in webhooks:
        webhook_url = webhook["url"]
        
        # --- SLACK FORMATI ---
        if "slack.com" in webhook_url.lower():
            blocks = []
            
            if new_status == "ENGELLİ":
                # Metin Bloğu
                msg_text = f"🚨 *{domain}* ENGELLENDİ! Lütfen *{next_domain if next_domain else 'yeni adrese'}* geçiniz."
                
                # EKSTRA BİLGİ: Yeni domain takibi
                if next_domain:
                    msg_text += f"\n🔄 *{next_domain}* otomatik takibe alındı."

                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": msg_text
                    }
                })
                
                # Resim Bloğu
                if image_url:
                    blocks.append({
                        "type": "image",
                        "image_url": image_url,
                        "alt_text": "Erişim Engeli Kanıtı"
                    })
            else:
                msg_text = f"ℹ️ *{domain}* Durumu: {new_status}"
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": msg_text
                    }
                })
            
            payload = {"blocks": blocks}
        
        # --- DISCORD / GENEL FORMAT ---
        else:
            if new_status == "ENGELLİ":
                msg_content = f"🚫 **{domain}** ENGELLENDİ."
                
                if next_domain: 
                    msg_content += f"\n👉 Yeni Adres: **{next_domain}**"
                    # EKSTRA BİLGİ: Yeni domain takibi
                    msg_content += f"\n🔄 **{next_domain}** otomatik takibe alındı."
                
                # DÜZELTME: Link önizlemesini (Double Preview) kaldırmak için 
                # buradaki 'Kanıt: http...' satırını kaldırdık.
                # Resim sadece aşağıdaki embed içinde görünecek.
                
                color = 15548997 # KIRMIZI
            else:
                msg_content = f"ℹ️ **{domain}** Durumu: {new_status}"
                color = 5763719 # YEŞİL
            
            payload = {
                "content": msg_content,
                "username": "BTK Bot",
                "embeds": []
            }
            
            # Embed Ayarları
            embed_obj = {
                "color": color
            }
            
            # Resmi Embed içine göm (Böylece tek ve büyük görünür)
            if image_url:
                embed_obj["title"] = "🔍 Kanıt Ekran Görüntüsü"
                embed_obj["description"] = f"Erişim durumu kontrol edildi. [Orijinal Resim]({image_url})"
                embed_obj["image"] = {"url": image_url}
            else:
                embed_obj["description"] = "Detaylı kontrol yapıldı."

            payload["embeds"].append(embed_obj)
        
        notification_queue.put({"type": "webhook", "url": webhook_url, "payload": payload})

def process_scan_result_and_print(domain, sonuc, prefix, index, total):
    eski = db.get_domain_status(domain)
    yeni = sonuc.durum
    
    db.update_stats(yeni)
    db.update_domain_status(domain, yeni) 
    
    degisim = (eski != yeni)
    degisim_from_error = (eski in ["HATA", "BİLİNMİYOR"])  # Hata durumundan gelen geçiş
    next_domain = increment_domain(domain) if yeni == "ENGELLİ" else None
    
    image_url = None
    local_image_path = None
    
    # Screenshot işlemleri (RAM ve Disk Desteği)

    target_users = db.get_users_for_domain(domain)
    
    # Linked Groups (Anahtarla bağlanmış grupları ekle)
    linked_groups = db.get_linked_chats_for_domain(domain)
    if linked_groups:
        # target_users listesine ekle (set yaparak duplicate önleyelim)
        current_set = set(target_users)
        for gid in linked_groups:
            current_set.add(gid)
        target_users = list(current_set)
    
    # Webhook var mı kontrol et (Gereksiz upload yapmamak için)
    # Sadece ENGELLİ durumunda ve webhook varsa upload gereklidir.
    has_webhooks = False
    if yeni == "ENGELLİ":
        # Target users içinde webhook tanımlı olan var mı bak
        for uid in target_users:
            if db.get_active_webhooks_for_domain(uid, domain):
                has_webhooks = True
                break

    # Screenshot işlemleri (RAM ve Disk Desteği)
    if sonuc.screenshot_paths:
        for path in sonuc.screenshot_paths:
            # 1. Önce Resmi Sunucuya Yükle (URL Al) - SADECE WEBHOOK VARSA
            if has_webhooks:
                image_url = upload_image_to_remote(path)
            
            # 2. Telegram için yerel kopya hazırla
            if isinstance(path, str) and os.path.exists(path):
                local_image_path = path
                break
            elif isinstance(path, io.BytesIO):
                # Telegram büyük dosyaları RAM'den atarken bazen hata verebilir,
                # garantilemek için geçici diske yazıyoruz.
                temp_name = f"temp_{domain}_{int(time.time())}.png"
                with open(temp_name, "wb") as f:
                    f.write(path.getvalue())
                local_image_path = temp_name
                break


    global_switch = None
    ultra_ss_active = db.get_setting("ultra_screenshots")

    # HATA ve BİLİNMİYOR durumlarında sadece admin kanalına bildir
    if yeni in ["HATA", "BİLİNMİYOR"]:
        if degisim or local_image_path:  # Durum değiştiyse VEYA screenshot varsa (hata kanıtı)
            admin_msg = f"⚠️ **Tarama Sorunu**\n🌍 `{domain}`\n📊 Durum: {yeni}\n📝 Detay: {sonuc.detay if hasattr(sonuc, 'detay') else '-'}"
            
            if local_image_path:
                notification_queue.put({
                    "type": "telegram_photo", "chat_id": ADMIN_CHANNEL_ID, 
                    "path": local_image_path, "caption": admin_msg, "delete_after": False
                })
            else:
                notification_queue.put({"type": "telegram_text", "chat_id": ADMIN_CHANNEL_ID, "text": admin_msg})
        # Kullanıcılara ve webhook'lara bildirim gönderme
    else:
        # TÜM değişimleri admin kanalına bildir
        if degisim:
            icon = "✅" if yeni == "TEMİZ" else "🚫" if yeni == "ENGELLİ" else "❓"
            admin_msg = f"{icon} **Durum Değişimi**\n🌍 `{domain}`\n📊 {eski} → {yeni}"
            notification_queue.put({"type": "telegram_text", "chat_id": ADMIN_CHANNEL_ID, "text": admin_msg})
        
        # Normal akış (TEMİZ ve ENGELLİ için)
        is_weekend = datetime.datetime.now().weekday() >= 5  # Cumartesi=5, Pazar=6
        
        for user_id in target_users:
            u_data = db.get_user_data(user_id)
            if not db.check_user_access(user_id)["access"]: continue
            
            user_wants_ultra_ss = u_data.get("ultra_enabled", True)
            # Ultra SS hafta sonu pasif
            is_ultra = (u_data.get("plan") == "ultra" and yeni == "TEMİZ" and local_image_path and ultra_ss_active and user_wants_ultra_ss and not is_weekend)

            # BİLDİRİM ŞARTI: (Değişim VE hata durumundan değilse) VEYA Engelli Durumu VEYA Ultra Modu
            should_notify = (degisim and not degisim_from_error) or (yeni == "ENGELLİ") or is_ultra

            if should_notify:
                # 1. Webhook (Resim URL'i ile)
                queue_webhook(user_id, domain, eski, yeni, image_url, next_domain)

                # 2. Telegram
                if is_ultra:
                    text = f"🛡️ **ULTRA KONTROL**\n🌍 `{domain}`\n✅ Durum: **TEMİZ**\n🕒 Saat: {datetime.datetime.now().strftime('%H:%M:%S')}"
                else:
                    if eski == "YENI" and yeni == "TEMİZ":
                        text = tg_conf.MESSAGES["new_domain_clean"].format(domain=domain)
                    else:
                        header = tg_conf.MESSAGES["report_header_change"] if degisim else tg_conf.MESSAGES["report_header_banned"]
                        if yeni == "ENGELLİ" and next_domain:
                             text = f"{header}\n🚫 *{domain}* engellendi.\n👉 Lütfen *{next_domain}* adresine geçiniz."
                        elif yeni == "ENGELLİ":
                             text = f"{header}\n🚫 *{domain}* engellendi."
                        else:
                             text = tg_conf.MESSAGES["report_body"].format(header=header, domain=domain, status=yeni)
                
                if local_image_path:
                    notification_queue.put({
                        "type": "telegram_photo", "chat_id": user_id, 
                        "path": local_image_path, "caption": text, "delete_after": False
                    })
                else:
                    notification_queue.put({"type": "telegram_text", "chat_id": user_id, "text": text})

            # 3. Oto-Geçiş
            if yeni == "ENGELLİ" and db.get_setting("auto_switch") and next_domain:
                if db.sil_domain(user_id, domain):
                    db.ekle_domain(user_id, next_domain)
                    notification_queue.put({"type": "telegram_text", "chat_id": user_id, "text": f"🔄 **Oto-Geçiş:** `{domain}` ➡️ `{next_domain}`"})
                    global_switch = f"🔄 Geçiş: {domain} ➜ {next_domain}"

    # Webhook güncellemesi
    if yeni == "ENGELLİ" and next_domain:
        db.update_webhook_domain_string(domain, next_domain)

    if global_switch:
        threading.Thread(target=start_manual_scan, args=(ADMIN_ID, [next_domain]), name="SwitchScan").start()

    # Geçici dosyayı sil
    if local_image_path:
        threading.Timer(15.0, lambda: os.remove(local_image_path) if os.path.exists(local_image_path) else None).start()

    icon = "✅" if yeni == "TEMİZ" else "🚫" if yeni == "ENGELLİ" else "⚠️"
    color = Colors.GREEN if yeni == "TEMİZ" else Colors.RED if yeni == "ENGELLİ" else Colors.YELLOW
    
    with print_lock:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 🤖 [{index}/{total}] 🌍 {domain} ➜ {color}{icon} {yeni}{Colors.RESET} (⏱️ {sonuc.sure}s)")
        if global_switch: print(f"           ↳ {global_switch}")
        if yeni == "HATA": print(f"           ↳ 📝 Detay: {sonuc.detay}")

def _single_manual_scan(args):
    idx, total, d = args
    with print_lock: print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ⏳ [{idx}/{total}] {d} taranıyor...")
    with get_scanner() as s:
        try:
            res = s.sorgula(d)
            process_scan_result_and_print(d, res, "Manuel", idx, total)
            if res.durum != "HATA":
                icon = "✅" if res.durum == "TEMİZ" else "🚫" if res.durum == "ENGELLİ" else "⚠️"
                return f"🌍 `{d}` ➜ {icon} **{res.durum.upper()}**"
        except Exception as e: logger.error(f"Hata: {e}")
    return None

def start_manual_scan(chat_id, domains):
    with scan_lock:
        if chat_id in active_user_scans:
            tg.send_message(chat_id, "⚠️ **Zaten devam eden bir taramanız var!**\nLütfen bitmesini bekleyin.")
            return
        active_user_scans.add(chat_id)

    def worker():
        try:
            tg.send_message(chat_id, f"🔍 {len(domains)} domain taranıyor...")
            total = len(domains)
            results = []
            print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] 🚀 [MANUEL] Başladı: {total} Görev")
            
            with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_SCANS) as executor:
                tasks = [(i+1, total, d) for i, d in enumerate(domains)]
                for res in executor.map(_single_manual_scan, tasks):
                    if res: results.append(res)
            
            summary = ("🔎 **Manuel Tarama Sonuçları**\n━━━━━━━━━━━━━━━━━━\n\n" + "\n".join(results) + "\n\n✅ **İşlem Tamamlandı!**") if results else "⚠️ Sonuç yok."
            tg.send_message(chat_id, summary)
        except Exception as e:
            logger.error(f"Worker hatası: {e}")
            tg.send_message(chat_id, "❌ Hata oluştu.")
        finally:
            with scan_lock: active_user_scans.discard(chat_id)

    threading.Thread(target=worker, name=f"ManualScan-{chat_id}").start()

# --- GÜNCELLENEN BACKGROUND LOOP ---
def background_loop():
    import os
    last_backup = ""; last_report = ""
    print("--> [Engine] Arka plan döngüsü başlatıldı.")
    print("--> [Takvim] Hafta İçi: 5dk | Hafta Sonu: 1 Saat")
    print("--> [Mesai]  08:00 - 21:30 arası aktiftir.")

    while True:
        try:
            now = datetime.datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            
            # 1. RAPORLAMA SAATİ (21:35 - 21:40)
            # Bu blok mesai saatinden bağımsız çalışır.
            if now.hour == 21:
                # Yedekleme
                if 35 <= now.minute < 40 and last_backup != date_str:
                    if os.path.exists("bot_data.db"):
                        notification_queue.put({"type": "telegram_doc", "chat_id": ADMIN_CHANNEL_ID, "path": "bot_data.db", "caption": "💾 **Günlük Yedek**"})
                    last_backup = date_str
            
                # İstatistik Raporu
                if 35 <= now.minute < 40 and last_report != date_str:
                    stats = db.get_stats(date_str)
                    txt = (f"📊 **Günlük Rapor**\n📅 Tarih: {stats['date']}\n━━━━━━━━━━━━━━\n🔢 Toplam: **{stats['total']}**\n✅ Temiz: {stats['TEMIZ']}\n🚫 Engelli: {stats['ENGELLİ']}\n⚠️ Hata: {stats['HATA']}")
                    chart = visuals.create_daily_stats_chart(stats)
                    if chart: notification_queue.put({"type": "telegram_chart", "chat_id": ADMIN_CHANNEL_ID, "chart": chart, "caption": txt})
                    else: notification_queue.put({"type": "telegram_text", "chat_id": ADMIN_CHANNEL_ID, "text": txt})
                    
                    if now.weekday() == 0: # Pazartesi Raporu
                        weekly_stats = db.get_weekly_stats()
                        w_txt = (f"📈 **Haftalık Rapor**\n🗓️ Dönem: {weekly_stats['period']}\n━━━━━━━━━━━━━━\n🔢 Toplam: **{weekly_stats['total']}**\n✅ Temiz: {weekly_stats['TEMIZ']}\n🚫 Engelli: {weekly_stats['ENGELLİ']}\n⚠️ Hata: {weekly_stats['HATA']}")
                        notification_queue.put({"type": "telegram_text", "chat_id": ADMIN_CHANNEL_ID, "text": w_txt})
                    last_report = date_str

            # 1.5 ÜYELİK SÜRESİ BİLDİRİMLERİ
            # 24 saat kala uyarı
            expiring_users = db.get_expiring_users(hours=24)
            for user in expiring_users:
                try:
                    expiry_formatted = user["expiry_date"][:16] if user["expiry_date"] else "-"
                    msg = tg_conf.MESSAGES["expiry_warning_24h"].format(expiry=expiry_formatted)
                    notification_queue.put({
                        "type": "telegram_text_with_button", 
                        "chat_id": user["user_id"], 
                        "text": msg,
                        "button_text": "💰 Satın Al",
                        "button_callback": "satin_al"
                    })
                    db.mark_user_notified(user["user_id"], 1)  # 1 = 24h uyarısı gönderildi
                    print(f"[{now.strftime('%H:%M:%S')}] ⏰ 24h uyarısı gönderildi: {user['user_id']}")
                except Exception as e:
                    print(f"Expiry warning error: {e}")
            
            # Süresi yeni dolanlar (ilk bildirim)
            expired_users = db.get_newly_expired_users()
            for user in expired_users:
                try:
                    msg = tg_conf.MESSAGES["expiry_ended"]
                    notification_queue.put({
                        "type": "telegram_text_with_button", 
                        "chat_id": user["user_id"], 
                        "text": msg,
                        "button_text": "💰 Satın Al",
                        "button_callback": "satin_al"
                    })
                    db.mark_user_notified(user["user_id"], 2)  # 2 = süre doldu bildirimi gönderildi
                    print(f"[{now.strftime('%H:%M:%S')}] ⛔ Süre doldu bildirimi: {user['user_id']}")
                except Exception as e:
                    print(f"Expiry ended error: {e}")
            
            # Tekrarlayan bildirim: Saat 09:00 ve 18:00'da tüm süresi dolmuş kullanıcılara
            if now.hour in [9, 18] and now.minute < 5:
                all_expired = db.get_all_expired_users()
                for user in all_expired:
                    try:
                        msg = tg_conf.MESSAGES["expiry_ended"]
                        notification_queue.put({
                            "type": "telegram_text_with_button", 
                            "chat_id": user["user_id"], 
                            "text": msg,
                            "button_text": "💰 Satın Al",
                            "button_callback": "satin_al"
                        })
                        print(f"[{now.strftime('%H:%M:%S')}] 🔔 Tekrar hatırlatma: {user['user_id']}")
                    except Exception as e:
                        pass  # Kullanıcı botu engellemiş olabilir

            # 1.6 WEBHOOK SÜRE BİLDİRİMLERİ
            # 24 saat kala uyarı
            expiring_webhooks = db.get_expiring_webhooks(hours=24)
            for wh in expiring_webhooks:
                try:
                    expiry_formatted = wh["expiry_date"][:16] if wh["expiry_date"] else "-"
                    msg = f"⏰ **Webhook Uyarısı**\n\n`{wh['name']}` webhook'unuzun süresi **24 saat** içinde dolacak!\n📅 Bitiş: {expiry_formatted}"
                    notification_queue.put({"type": "telegram_text", "chat_id": wh["user_id"], "text": msg})
                    print(f"[{now.strftime('%H:%M:%S')}] ⏰ Webhook uyarısı: {wh['name']}")
                except Exception as e:
                    print(f"Webhook warning error: {e}")
            
            # Süresi dolmuş webhookları pasife al ve bildir
            expired_webhooks = db.get_expired_webhooks()
            for wh in expired_webhooks:
                try:
                    db.deactivate_webhook(wh["id"])
                    msg = f"⛔ **Webhook Süresi Doldu**\n\n`{wh['name']}` webhook'unuz pasife alındı.\n\nYenilemek için /webhooks yazın."
                    notification_queue.put({"type": "telegram_text", "chat_id": wh["user_id"], "text": msg})
                    print(f"[{now.strftime('%H:%M:%S')}] ⛔ Webhook süresi doldu: {wh['name']}")
                except Exception as e:
                    print(f"Webhook expired error: {e}")

            # 2. ÇALIŞMA SAATİ VE ARALIK BELİRLEME
            current_mins = now.hour * 60 + now.minute
            start_mins = 8 * 60         # 08:00
            end_mins = 21 * 60 + 31     # 21:31
            
            is_working_hours = (start_mins <= current_mins <= end_mins)
            is_weekend = (now.weekday() >= 5) # 5=Cmt, 6=Paz
            
            # Aralık (Interval) Belirleme
            if is_working_hours:
                if is_weekend:
                    interval = 60 # Hafta sonu 1 saat
                    mode_str = "Hafta Sonu Modu (1 Saat)"
                else:
                    interval = 5  # Hafta içi 5 dakika
                    mode_str = "Hafta İçi Modu (5 Dk)"
            else:
                interval = 60 # Gece bekleme süresi
                mode_str = "Gece Modu (Pasif)"

            # 3. TARAMA (Sadece Mesai Saatlerinde)
            active = db.get_setting("system_active")
            # Ultra kontrol periyodu (Her saat başı veya buçuğunda)
            is_ultra_period = (now.minute < 5) or (30 <= now.minute < 35)

            if active and is_working_hours:
                users_domains = db.get_all_users_domains()
                tasks = []
                seen = set()
                domains_with_ultra = set()
                
                for uid, doms in users_domains.items():
                    if not db.check_user_access(uid)["access"]: continue
                    user_plan = db.get_user_data(uid).get("plan")
                    for d in doms:
                        if d not in seen:
                            tasks.append((uid, d)); seen.add(d)
                        if user_plan == "ultra" and is_ultra_period:
                            domains_with_ultra.add(d)
                
                total = len(tasks)
                if total > 0:
                    print(f"\n[{now.strftime('%H:%M:%S')}] 🚀 [OTO] Başladı ({mode_str}): {total} Görev")
                    if is_ultra_period and domains_with_ultra: 
                        print(f"💎 [ULTRA] Periyodik Rapor (Hedef: {len(domains_with_ultra)})")

                    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_SCANS) as executor:
                        def _bg_scan_wrapper(args):
                            u, d, i, t = args
                            force_ss = (d in domains_with_ultra)
                            with print_lock: print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ⏳ [{i}/{t}] {d} taranıyor...")
                            with get_scanner() as s:
                                try:
                                    res = s.sorgula(d, force_screenshot=force_ss)
                                    process_scan_result_and_print(d, res, "Oto", i, t)
                                except Exception as e: logger.error(f"Hata ({d}): {e}")

                        bg_tasks = []
                        for i, (u, d) in enumerate(tasks, 1):
                            bg_tasks.append((u, d, i, total))
                        list(executor.map(_bg_scan_wrapper, bg_tasks))
            elif not is_working_hours:
                 print(f"[{now.strftime('%H:%M:%S')}] 🌙 Mesai dışı (08:00-21:30). Tarama yapılmıyor.")

            # 4. HİZALAMA VE BEKLEME (Test modu yerine gerçek hizalama)
            # Şu anki zamana göre bir sonraki interval dilimini hesapla
            now = datetime.datetime.now()
            
            # Matematiksel olarak bir sonraki "tam" dilimi bul
            # Örnek: interval=60 ise ve saat 09:15 ise -> hedef 10:00
            # Örnek: interval=5  ise ve saat 09:12 ise -> hedef 09:15
            
            current_epoch_mins = int(time.time() / 60)
            next_epoch_mins = (current_epoch_mins // interval + 1) * interval
            wait_minutes = next_epoch_mins - current_epoch_mins
            wait_sec = wait_minutes * 60 - now.second
            
            # Güvenlik marjı (Negatif çıkarsa hemen çalışma)
            if wait_sec <= 0: wait_sec = 60

            next_run_time = now + datetime.timedelta(seconds=wait_sec)
            print(f"[{now.strftime('%H:%M:%S')}] 💤 Bekleniyor: {next_run_time.strftime('%H:%M:%S')} ({int(wait_sec)}s) - {mode_str}")
            
            time.sleep(wait_sec)

        except Exception as e:
            logger.error(f"Loop hatası: {e}")
            time.sleep(60)
