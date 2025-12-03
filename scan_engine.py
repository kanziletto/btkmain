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
    MAX_CONCURRENT_SCANS = 2
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

def upload_image_to_remote(image_path):
    try:
        with open(image_path, 'rb') as f:
            response = upload_session.post(IMAGE_UPLOAD_URL, files={'file': f}, timeout=30)
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
                    # Debug Log
                    print(f"📡 Webhook Tetiklendi... ({url[:30]}...)")
                    
                    # Basit Requests (Session yok)
                    r = requests.post(url, json=payload, timeout=10)
                    
                    if r.status_code not in [200, 201, 204]:
                        print(f"❌ Webhook Hatası (HTTP {r.status_code}): {r.text}")
                    else:
                        print(f"✅ Webhook Başarıyla İletildi! (HTTP {r.status_code})")
                        
                except Exception as e:
                    print(f"❌ Webhook Bağlantı Hatası: {e}")

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
            
            elif t_type == "telegram_chart":
                 tg.send_photo(task["chat_id"], task["chart"], caption=task["caption"])

        except Exception as e:
            print(f"Bildirim Worker Hatası: {e}")
        finally:
            notification_queue.task_done()

threading.Thread(target=notification_worker, daemon=True, name="Notifier").start()

def queue_webhook(user_id, domain, old_status, new_status, image_url=None, next_domain=None):
    # 1. Webhookları Bul
    webhooks = db.get_active_webhooks_for_domain(user_id, domain)
    
    if not webhooks:
        return
    
    print(f"🔗 {len(webhooks)} Webhook bulundu. Hazırlanıyor...")
    
    for webhook in webhooks:
        webhook_url = webhook["url"]
        
        # SLACK FORMATI (BASİTLEŞTİRİLMİŞ TEST)
        if "slack.com" in webhook_url.lower():
            if new_status == "ENGELLİ":
                # Sadece düz yazı (Text Only Payload)
                msg = f"🚨 *{domain}* ENGELLENDİ! Lütfen *{next_domain if next_domain else 'yeni adrese'}* geçiniz."
                if image_url:
                    msg += f"\n📸 Kanıt: {image_url}"
                
                payload = {"text": msg}
            else:
                # Temiz veya diğer durumlar
                msg = f"ℹ️ *{domain}* Durumu: {new_status}"
                payload = {"text": msg}
        
        # GENEL / DISCORD FORMATI
        else:
            msg = f"{domain} engellendi." if new_status == "ENGELLİ" else f"{domain} durumu: {new_status}"
            payload = {
                "content": msg,
                "username": "BTK Bot",
                "embeds": []
            }
            if image_url:
                payload["embeds"].append({
                    "title": "Kanıt",
                    "image": {"url": image_url},
                    "color": 15158332 if new_status == "ENGELLİ" else 3066993
                })
        
        notification_queue.put({"type": "webhook", "url": webhook_url, "payload": payload})

def process_scan_result_and_print(domain, sonuc, prefix, index, total):
    eski = db.get_domain_status(domain)
    yeni = sonuc.durum
    db.update_stats(yeni)
    db.update_domain_status(domain, yeni) 
    
    degisim = (eski != yeni) and (eski != "YENI")
    next_domain = increment_domain(domain) if yeni == "ENGELLİ" else None
    
    image_url = None
    local_image_path = None
    
    if sonuc.screenshot_paths:
        for path in sonuc.screenshot_paths:
            if isinstance(path, str) and os.path.exists(path):
                local_image_path = path
                image_url = upload_image_to_remote(path)
                break
            elif not isinstance(path, str):
                temp_name = f"temp_{domain}_{int(time.time())}.png"
                with open(temp_name, "wb") as f:
                    f.write(path.getvalue())
                local_image_path = temp_name
                image_url = upload_image_to_remote(temp_name)
                break

    target_users = db.get_users_for_domain(domain)
    global_switch = None

    if yeni == "ENGELLİ" and next_domain:
        db.update_webhook_domain_string(domain, next_domain)

    ultra_ss_active = db.get_setting("ultra_screenshots")

    for user_id in target_users:
        u_data = db.get_user_data(user_id)
        if not db.check_user_access(user_id)["access"]: continue
        
        user_wants_ultra_ss = u_data.get("ultra_enabled", True)
        is_ultra = (u_data.get("plan") == "ultra" and yeni == "TEMİZ" and local_image_path and ultra_ss_active and user_wants_ultra_ss)

        # 1. Webhook
        if degisim or yeni == "ENGELLİ" or is_ultra:
            queue_webhook(user_id, domain, eski, yeni, image_url, next_domain)

        # 2. Telegram
        if degisim or yeni == "ENGELLİ" or is_ultra:
            if is_ultra:
                text = f"🛡️ **ULTRA KONTROL**\n🌍 `{domain}`\n✅ Durum: **TEMİZ**\n🕒 Saat: {datetime.datetime.now().strftime('%H:%M:%S')}"
            else:
                header = tg_conf.MESSAGES["report_header_change"] if degisim else tg_conf.MESSAGES["report_header_banned"]
                if yeni == "ENGELLİ" and next_domain:
                     text = f"{header}\n🚫 *{domain}* engellendi.\n👉 Lütfen *{next_domain}* adresine geçiniz."
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

    if global_switch:
        threading.Thread(target=start_manual_scan, args=(ADMIN_ID, [next_domain]), name="SwitchScan").start()

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
            tg.send_message(chat_id, f"🔍 {len(domains)} domain taranıyor... (Hızlandırılmış Mod)")
            total = len(domains)
            results = []
            print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] 🚀 [MANUEL] Başladı: {total} Görev (Parallel: {MAX_CONCURRENT_SCANS})")
            
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

def background_loop():
    import os
    last_backup = ""; last_report = ""
    print("--> [Engine] Arka plan döngüsü başladı.")
    
    def wait_until_next_5min():
        now = datetime.datetime.now()
        next_min = ((now.minute // 5) + 1) * 5
        if next_min >= 60: next_time = (now + datetime.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        else: next_time = now.replace(minute=next_min, second=0, microsecond=0)
        wait_sec = (next_time - now).total_seconds()
        if wait_sec <= 0: wait_sec += 300; next_time += datetime.timedelta(minutes=5)
        print(f"[{now.strftime('%H:%M:%S')}] 💤 Tur Tamamlandı. {next_time.strftime('%H:%M:%S')} bekleniyor ({int(wait_sec)}s)...")
        time.sleep(wait_sec)

    wait_until_next_5min()
    
    while True:
        try:
            now = datetime.datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            
            # --- TEST: BAKIM & RAPOR (02:45) ---
            if now.hour == 3:
                if 15 <= now.minute < 20 and last_backup != date_str:
                    if os.path.exists("bot_data.db"):
                        notification_queue.put({"type": "telegram_doc", "chat_id": ADMIN_CHANNEL_ID, "path": "bot_data.db", "caption": "💾 **Günlük Yedek (Test: 03:15)**"})
                    last_backup = date_str
            
                if 15 <= now.minute < 20 and last_report != date_str:
                    stats = db.get_stats(date_str)
                    txt = (f"📊 **Günlük Rapor (Test)**\n📅 Tarih: {stats['date']}\n━━━━━━━━━━━━━━\n🔢 Toplam: **{stats['total']}**\n✅ Temiz: {stats['TEMIZ']}\n🚫 Engelli: {stats['ENGELLİ']}\n⚠️ Hata: {stats['HATA']}")
                    chart = visuals.create_daily_stats_chart(stats)
                    if chart: notification_queue.put({"type": "telegram_chart", "chat_id": ADMIN_CHANNEL_ID, "chart": chart, "caption": txt})
                    else: notification_queue.put({"type": "telegram_text", "chat_id": ADMIN_CHANNEL_ID, "text": txt})
                    
                    if now.weekday() == 0: 
                        weekly_stats = db.get_weekly_stats()
                        w_txt = (f"📈 **Haftalık Rapor**\n🗓️ Dönem: {weekly_stats['period']}\n━━━━━━━━━━━━━━\n🔢 Toplam: **{weekly_stats['total']}**\n✅ Temiz: {weekly_stats['TEMIZ']}\n🚫 Engelli: {weekly_stats['ENGELLİ']}\n⚠️ Hata: {weekly_stats['HATA']}")
                        notification_queue.put({"type": "telegram_text", "chat_id": ADMIN_CHANNEL_ID, "text": w_txt})
                    last_report = date_str

            active = db.get_setting("system_active")
            in_working_hours = True 
            is_ultra_period = (now.minute < 5) or (30 <= now.minute < 35)

            if active and in_working_hours:
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
                    print(f"\n[{now.strftime('%H:%M:%S')}] 🚀 [OTO] Başladı: {total} Görev (Parallel: {MAX_CONCURRENT_SCANS})")
                    if is_ultra_period: print(f"💎 [ULTRA] Periyodik Rapor (Hedef: {len(domains_with_ultra)})")

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
            
            def wait_until_next_minute():
                now = datetime.datetime.now()
                next_time = (now + datetime.timedelta(minutes=1)).replace(second=0, microsecond=0)
                wait_sec = (next_time - now).total_seconds()
                if wait_sec <= 0: wait_sec += 60
                print(f"[{now.strftime('%H:%M:%S')}] 💤 Test Modu (1dk): {next_time.strftime('%H:%M:%S')} bekleniyor ({int(wait_sec)}s)...")
                time.sleep(wait_sec)
            
            wait_until_next_minute()

        except Exception as e:
            logger.error(f"Loop: {e}")
            time.sleep(60)
