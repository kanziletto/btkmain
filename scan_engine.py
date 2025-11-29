import time
import threading
import queue
import datetime
import os
import sys
from contextlib import contextmanager
from btk import BTKScanner
from database import Database
from utils import logger
import telegram_bot as tg 
import telegram_config as tg_conf
import visuals
import re

MAX_SCANS = 2
scanner_pool = queue.Queue(maxsize=MAX_SCANS)
db = Database()

try:
    for i in range(MAX_SCANS):
        scanner_pool.put(BTKScanner())
        print(f"--> [Engine] Scanner {i+1} hazır.")
except: pass

@contextmanager
def get_scanner():
    s = scanner_pool.get()
    try:
        yield s
    finally:
        scanner_pool.put(s)

def update_progress(prefix, current, total, domain, status, captcha=""):
    sys.stdout.write(f"\r\033[K[{datetime.datetime.now().strftime('%H:%M:%S')}] {prefix}: {current}/{total} | {domain} -> {status} | Cap: {captcha}")
    sys.stdout.flush()

def increment_domain(domain):
    matches = list(re.finditer(r'\d+', domain))
    if not matches: return None
    match = matches[-1]
    try:
        new = int(match.group()) + 1
        return domain[:match.start()] + str(new) + domain[match.end():]
    except: return None

def process_scan_result(chat_id, domain, sonuc):
    eski = db.get_domain_status(domain)
    yeni = sonuc.durum
    db.update_stats(yeni)
    db.update_domain_status(domain, yeni) 
    
    degisim = (eski != yeni) and (eski != "YENI")
    
    if "HATA" in yeni:
        tg.send_message(tg_conf.ADMIN_CHANNEL_ID, f"⚠️ HATA: {domain} -> {yeni}")
        return

    if yeni == "ENGELLİ" and db.get_setting("auto_switch"):
        new_dom = increment_domain(domain)
        if new_dom:
            db.ekle_domain(chat_id, new_dom)
            db.sil_domain(chat_id, domain)
            tg.send_message(chat_id, f"🔄 **Oto-Geçiş:** `{domain}` ➡️ `{new_dom}`")
            start_manual_scan(chat_id, [new_dom])

    if degisim or yeni == "ENGELLİ":
        header = tg_conf.MESSAGES["report_header_change"] if degisim else tg_conf.MESSAGES["report_header_banned"]
        text = tg_conf.MESSAGES["report_body"].format(header=header, domain=domain, status=yeni)
        
        photo_sent = False
        if sonuc.screenshot_paths:
            for path in sonuc.screenshot_paths:
                if "kanit" in path and os.path.exists(path):
                    with open(path, 'rb') as f:
                        tg.send_photo(chat_id, f, caption=text)
                        photo_sent = True
                    try: os.remove(path); break
                    except: pass
        
        if not photo_sent:
            tg.send_message(chat_id, text)

def start_manual_scan(chat_id, domains):
    def worker():
        tg.send_message(chat_id, f"🔍 {len(domains)} domain taranıyor...")
        total = len(domains)
        
        results = []
        
        for idx, d in enumerate(domains, 1):
            with get_scanner() as scanner:
                try:
                    res = scanner.sorgula(d)
                    process_scan_result(chat_id, d, res)
                    
                    if res.durum == "HATA":
                        continue
                    
                    status_text = res.durum.lower()
                    results.append(f"{d} {status_text}")
                    
                    update_progress("Manuel", idx, total, d, res.durum, res.captcha_text)
                except Exception as e:
                    logger.error(f"Manuel tarama hatası ({d}): {e}")
                    tg.send_message(tg_conf.ADMIN_CHANNEL_ID, f"⚠️ **Manuel Tarama Hatası**\n👤 Kullanıcı: `{chat_id}`\n🌐 Domain: `{d}`\n❌ Hata: {str(e)}")
        
        sys.stdout.write("\n")
        
        if not results:
            summary = "✅ **Tarama Tamamlandı!**\n\n"
            summary += "⚠️ Sonuç alınamadı. Lütfen daha sonra tekrar deneyin."
        else:
            summary = "✅ **Tarama Tamamlandı!**\n\n"
            summary += "\n".join(results)
        
        tg.send_message(chat_id, summary)
    
    threading.Thread(target=worker, name="ManualScan").start()

def background_loop():
    import os
    last_backup = ""
    last_report = ""
    
    print("--> [Engine] Arka plan döngüsü başladı.")
    
    while True:
        try:
            now = datetime.datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            
            if now.hour == 0:
                if now.minute == 0 and last_backup != date_str:
                    if os.path.exists("bot_data.db"):
                        with open("bot_data.db", 'rb') as f: 
                            tg.send_document(tg_conf.ADMIN_ID, f, caption="💾 Yedek")
                    last_backup = date_str
                
                if now.minute == 5 and last_report != date_str:
                    stats = db.get_stats()
                    chart = visuals.create_daily_stats_chart(stats)
                    txt = f"🕛 Rapor: {stats['total']} İşlem"
                    if chart: tg.send_photo(tg_conf.ADMIN_ID, chart, caption=txt)
                    else: tg.send_message(tg_conf.ADMIN_ID, txt)
                    last_report = date_str

            active = db.get_setting("system_active")
            mesai_start = now.replace(hour=8, minute=0, second=0, microsecond=0)
            mesai_end = now.replace(hour=21, minute=30, second=0, microsecond=0)
            
            is_weekend = now.weekday() >= 5
            in_working_hours = mesai_start <= now <= mesai_end
            
            if active and in_working_hours:
                users_domains = db.get_all_users_domains()
                if users_domains:
                    tasks = []
                    seen_domains = set()
                    
                    for uid, doms in users_domains.items():
                        status = db.check_user_access(uid)
                        if not status["access"]: 
                            continue
                        
                        for d in doms:
                            if d not in seen_domains:
                                tasks.append((uid, d))
                                seen_domains.add(d)
                    
                    total_tasks = len(tasks)
                    if total_tasks > 0:
                        processed = 0

                        def task_worker(task):
                            nonlocal processed
                            uid, dom = task
                            with get_scanner() as s:
                                try:
                                    res = s.sorgula(dom)
                                    process_scan_result(uid, dom, res)
                                    processed += 1
                                    update_progress("Oto", processed, total_tasks, dom, res.durum, res.captcha_text)
                                except: pass

                        threads = []
                        for t in tasks:
                            th = threading.Thread(target=task_worker, args=(t,), name="AutoScan")
                            th.start()
                            threads.append(th)
                            time.sleep(0.2)
                        
                        for th in threads: th.join()
                        sys.stdout.write("\n")
                
                if is_weekend:
                    logger.info("📅 Hafta sonu modu: 30 dakika bekleniyor...")
                    time.sleep(1800)
                else:
                    logger.info("📅 Hafta içi modu: 5 dakika bekleniyor...")
                    time.sleep(300)
            else:
                if not in_working_hours:
                    next_check = mesai_start if now < mesai_start else mesai_start + datetime.timedelta(days=1)
                    wait_minutes = int((next_check - now).total_seconds() / 60)
                    logger.info(f"😴 Mesai dışı. Bir sonraki mesai: {next_check.strftime('%H:%M')} ({wait_minutes} dakika sonra)")
                
                time.sleep(300)

        except Exception as e:
            logger.error(f"Loop Hatası: {e}")
            time.sleep(60)

