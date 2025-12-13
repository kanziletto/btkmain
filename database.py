import sqlite3
import datetime
import os
import threading
from dateutil.parser import parse
from config import ADMIN_ID, DB_FILE

class Database:
    def __init__(self):
        self.db_path = DB_FILE
        self._lock = threading.Lock()
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self):
        with self._lock:
            conn = self._get_conn()
            c = conn.cursor()
            c.execute("PRAGMA journal_mode=WAL;")
            
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                         user_id TEXT PRIMARY KEY,
                         plan TEXT,
                         start_date TEXT,
                         expiry_date TEXT,
                         notified_expiry INTEGER DEFAULT 0,
                         ultra_enabled INTEGER DEFAULT 1,
                         username TEXT
                         )''')
            
            try: c.execute("ALTER TABLE users ADD COLUMN ultra_enabled INTEGER DEFAULT 1")
            except: pass
            
            try: c.execute("ALTER TABLE users ADD COLUMN username TEXT")
            except: pass

            c.execute('''CREATE TABLE IF NOT EXISTS domains (
                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                         user_id TEXT,
                         domain TEXT,
                         UNIQUE(user_id, domain)
                         )''')

            c.execute('''CREATE TABLE IF NOT EXISTS notification_links (
                          key TEXT PRIMARY KEY,
                          domain TEXT,
                          owner_id TEXT,
                          linked_chat_id TEXT
                          )''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS status (domain TEXT PRIMARY KEY, status TEXT, last_check TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS stats (date TEXT PRIMARY KEY, total INTEGER DEFAULT 0, clean INTEGER DEFAULT 0, banned INTEGER DEFAULT 0, error INTEGER DEFAULT 0)''')
            c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value INTEGER)''')
            c.execute('''CREATE TABLE IF NOT EXISTS webhooks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, name TEXT, url TEXT, domains TEXT, expiry_date TEXT, active INTEGER DEFAULT 1)''')
            
            # Ödeme kayıtları tablosu
            c.execute('''CREATE TABLE IF NOT EXISTS payments (
                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                         user_id TEXT,
                         invoice_id TEXT UNIQUE,
                         amount REAL,
                         currency TEXT DEFAULT 'USDT',
                         plan_type TEXT,
                         days INTEGER,
                         status TEXT DEFAULT 'pending',
                         created_at TEXT,
                         paid_at TEXT
                         )''')
            
            # Referans sistemi tablosu
            c.execute('''CREATE TABLE IF NOT EXISTS referrals (
                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                         referrer_id TEXT,
                         referred_id TEXT UNIQUE,
                         status TEXT DEFAULT 'pending',
                         reward_days INTEGER DEFAULT 0,
                         created_at TEXT
                         )''')

            c.execute("SELECT * FROM users WHERE user_id=?", (str(ADMIN_ID),))
            if not c.fetchone():
                now = str(datetime.datetime.now())
                c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", (str(ADMIN_ID), "admin", now, "2099-12-31 23:59:59", 0, 1))

            defaults = [("silent_mode", 1), ("auto_switch", 1), ("system_active", 1), ("ultra_screenshots", 1)]
            for key, val in defaults:
                c.execute("INSERT OR IGNORE INTO settings VALUES (?, ?)", (key, val))

            conn.commit()
            conn.close()

    def register_user(self, user_id: str, username: str = None):
        with self._lock:
            conn = self._get_conn(); c = conn.cursor()
            if c.execute("SELECT * FROM users WHERE user_id=?", (str(user_id),)).fetchone(): conn.close(); return False
            now = datetime.datetime.now(); expiry = now + datetime.timedelta(days=2)
            c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", (str(user_id), "trial", str(now), str(expiry), 0, 1, username))
            conn.commit(); conn.close(); return True

    def register_user_scheduled(self, user_id: str, start_monday=False, username: str = None):
        with self._lock:
            conn = self._get_conn(); c = conn.cursor()
            if c.execute("SELECT * FROM users WHERE user_id=?", (str(user_id),)).fetchone(): conn.close(); return False, None, None
            now = datetime.datetime.now()
            if start_monday:
                days_until = (7 - now.weekday()) % 7
                if days_until == 0 and now.hour >= 8: days_until = 7
                start = (now + datetime.timedelta(days=days_until)).replace(hour=8, minute=0, second=0, microsecond=0)
            else: start = now
            expiry = start + datetime.timedelta(hours=48)
            c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", (str(user_id), "trial", str(start), str(expiry), 0, 1, username))
            conn.commit(); conn.close(); return True, start, expiry

    def check_user_access(self, user_id: str) -> dict:
        if str(user_id) == str(ADMIN_ID): return {"access": True, "plan": "admin", "msg": "Admin"}
        conn = self._get_conn(); row = conn.execute("SELECT plan, start_date, expiry_date FROM users WHERE user_id=?", (str(user_id),)).fetchone(); conn.close()
        if not row: return {"access": False, "plan": "none", "msg": "Kayıt yok."}
        try:
            if datetime.datetime.now() < parse(row[1]): return {"access": False, "plan": "scheduled", "msg": "Başlamadı."}
            if datetime.datetime.now() > parse(row[2]): return {"access": False, "plan": "expired", "msg": "Süre doldu."}
        except: return {"access": False, "plan": "error", "msg": "Hata."}
        return {"access": True, "plan": row[0], "msg": "Aktif"}

    def get_user_data(self, user_id):
        conn = self._get_conn(); c = conn.cursor(); c.execute("SELECT * FROM users WHERE user_id=?", (str(user_id),)); row = c.fetchone(); conn.close()
        if row: return {"plan": row[1], "start_date": row[2], "expiry_date": row[3], "ultra_enabled": bool(row[5]) if len(row)>5 else True, "username": row[6] if len(row)>6 else None}
        return {}

    def toggle_user_ultra(self, user_id):
        with self._lock:
            conn = self._get_conn(); c = conn.cursor()
            c.execute("SELECT ultra_enabled FROM users WHERE user_id=?", (str(user_id),))
            row = c.fetchone()
            if row:
                new_val = 0 if row[0] else 1
                c.execute("UPDATE users SET ultra_enabled=? WHERE user_id=?", (new_val, str(user_id))); conn.commit(); conn.close()
                return bool(new_val)
            conn.close(); return False

    def set_premium(self, user_id: str, days: int, username: str = None):
        with self._lock:
            conn = self._get_conn(); now = datetime.datetime.now(); expiry = now + datetime.timedelta(days=days)
            # Mevcut username'i korumak veya güncellemek için mantık gerekebilir ama basitçe güncelleyelim
            conn.execute("INSERT OR REPLACE INTO users (user_id, plan, start_date, expiry_date, notified_expiry, ultra_enabled, username) VALUES (?, ?, ?, ?, ?, ?, ?)", (str(user_id), "premium", str(now), str(expiry), 0, 1, username))
            conn.commit(); conn.close(); return str(expiry)

    def set_ultra(self, user_id: str, days: int, username: str = None):
        with self._lock:
            conn = self._get_conn(); now = datetime.datetime.now(); expiry = now + datetime.timedelta(days=days)
            conn.execute("INSERT OR REPLACE INTO users (user_id, plan, start_date, expiry_date, notified_expiry, ultra_enabled, username) VALUES (?, ?, ?, ?, ?, ?, ?)", (str(user_id), "ultra", str(now), str(expiry), 0, 1, username))
            conn.commit(); conn.close(); return str(expiry)

    def get_expiring_users(self, hours=24):
        """24 saat içinde süresi dolacak VE henüz uyarılmamış kullanıcıları getirir.
        notified_expiry: 0=bildirim yok, 1=24h uyarısı gönderildi, 2=süre doldu bildirimi gönderildi
        """
        conn = self._get_conn()
        now = datetime.datetime.now()
        future = now + datetime.timedelta(hours=hours)
        
        # Şu andan itibaren 24 saat içinde süresi dolacak VE notified_expiry=0 olan kullanıcılar
        rows = conn.execute("""
            SELECT user_id, plan, expiry_date FROM users 
            WHERE expiry_date > ? AND expiry_date <= ? AND notified_expiry = 0 AND plan != 'admin'
        """, (str(now), str(future))).fetchall()
        conn.close()
        
        return [{"user_id": r[0], "plan": r[1], "expiry_date": r[2]} for r in rows]

    def get_newly_expired_users(self):
        """Süresi yeni dolmuş VE henüz 'süre doldu' bildirimi almamış kullanıcılar.
        notified_expiry < 2 olanlar (0 veya 1)
        """
        conn = self._get_conn()
        now = str(datetime.datetime.now())
        
        rows = conn.execute("""
            SELECT user_id, plan, expiry_date FROM users 
            WHERE expiry_date < ? AND notified_expiry < 2 AND plan != 'admin'
        """, (now,)).fetchall()
        conn.close()
        
        return [{"user_id": r[0], "plan": r[1], "expiry_date": r[2]} for r in rows]

    def get_all_expired_users(self):
        """Tüm süresi dolmuş kullanıcıları getirir (tekrarlayan bildirim için)."""
        conn = self._get_conn()
        now = str(datetime.datetime.now())
        
        rows = conn.execute("""
            SELECT user_id, plan, expiry_date FROM users 
            WHERE expiry_date < ? AND plan != 'admin'
        """, (now,)).fetchall()
        conn.close()
        
        return [{"user_id": r[0], "plan": r[1], "expiry_date": r[2]} for r in rows]

    def mark_user_notified(self, user_id, notification_type):
        """Kullanıcıya bildirim gönderildiğini işaretle.
        notification_type: 1=24h uyarısı gönderildi, 2=süre doldu bildirimi gönderildi
        """
        with self._lock:
            conn = self._get_conn()
            conn.execute("UPDATE users SET notified_expiry = ? WHERE user_id = ?", (notification_type, str(user_id)))
            conn.commit()
            conn.close()

    # --- ÖDEME SİSTEMİ ---
    
    def create_payment(self, user_id: str, invoice_id: str, amount: float, currency: str, plan_type: str, days: int):
        """Yeni ödeme kaydı oluşturur (pending durumunda)"""
        with self._lock:
            conn = self._get_conn()
            now = str(datetime.datetime.now())
            try:
                conn.execute("""
                    INSERT INTO payments (user_id, invoice_id, amount, currency, plan_type, days, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
                """, (str(user_id), invoice_id, amount, currency, plan_type, days, now))
                conn.commit()
                return True
            except Exception as e:
                print(f"Payment create error: {e}")
                return False
            finally:
                conn.close()
    
    def confirm_payment(self, invoice_id: str) -> dict:
        """
        Ödemeyi onaylar ve kullanıcının planını aktive eder.
        Mevcut süreye ekleme yapar (süre uzatma).
        
        Returns:
            dict: {"success": bool, "user_id": str, "new_expiry": str}
        """
        with self._lock:
            conn = self._get_conn()
            c = conn.cursor()
            
            # Ödeme kaydını bul
            c.execute("SELECT user_id, plan_type, days, status FROM payments WHERE invoice_id = ?", (invoice_id,))
            row = c.fetchone()
            
            if not row:
                conn.close()
                return {"success": False, "error": "Fatura bulunamadı"}
            
            user_id, plan_type, days, status = row
            
            if status == "paid":
                conn.close()
                return {"success": False, "error": "Zaten onaylanmış"}
            
            # Mevcut süreyi kontrol et
            c.execute("SELECT expiry_date FROM users WHERE user_id = ?", (user_id,))
            user_row = c.fetchone()
            
            now = datetime.datetime.now()
            
            if user_row and user_row[0]:
                try:
                    current_expiry = datetime.datetime.strptime(user_row[0][:19], "%Y-%m-%d %H:%M:%S")
                    # Mevcut süre hâlâ aktifse, ona ekle
                    if current_expiry > now:
                        new_expiry = current_expiry + datetime.timedelta(days=days)
                    else:
                        new_expiry = now + datetime.timedelta(days=days)
                except:
                    new_expiry = now + datetime.timedelta(days=days)
            else:
                new_expiry = now + datetime.timedelta(days=days)
            
            # Kullanıcı planını güncelle - Username korunmalı
            current_username = None
            if user_row and len(user_row) > 1: # user_row sorgusu sadece expiry_date çekiyor, tekrar çekelim
                 tmp_c = conn.execute("SELECT username FROM users WHERE user_id=?", (user_id,))
                 tmp_r = tmp_c.fetchone()
                 if tmp_r: current_username = tmp_r[0]

            c.execute("""
                INSERT OR REPLACE INTO users (user_id, plan, start_date, expiry_date, notified_expiry, ultra_enabled, username)
                VALUES (?, ?, ?, ?, 0, 1, ?)
            """, (user_id, plan_type, str(now), str(new_expiry), current_username))
            
            # Ödeme durumunu güncelle
            c.execute("UPDATE payments SET status = 'paid', paid_at = ? WHERE invoice_id = ?", (str(now), invoice_id))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "user_id": user_id,
                "plan": plan_type,
                "days": days,
                "new_expiry": str(new_expiry)
            }
    
    def get_payment_history(self, user_id: str) -> list:
        """Kullanıcının ödeme geçmişini getirir"""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT invoice_id, amount, currency, plan_type, days, status, created_at, paid_at 
            FROM payments WHERE user_id = ? ORDER BY created_at DESC
        """, (str(user_id),)).fetchall()
        conn.close()
        
        return [{
            "invoice_id": r[0], "amount": r[1], "currency": r[2], 
            "plan": r[3], "days": r[4], "status": r[5],
            "created_at": r[6], "paid_at": r[7]
        } for r in rows]
    
    def get_pending_payment(self, user_id: str) -> dict:
        """Kullanıcının bekleyen ödemesini getirir (varsa)"""
        conn = self._get_conn()
        row = conn.execute("""
            SELECT invoice_id, amount, currency, plan_type, days, created_at 
            FROM payments WHERE user_id = ? AND status = 'pending' 
            ORDER BY created_at DESC LIMIT 1
        """, (str(user_id),)).fetchone()
        conn.close()
        
        if row:
            return {
                "invoice_id": row[0], "amount": row[1], "currency": row[2],
                "plan": row[3], "days": row[4], "created_at": row[5]
            }
        return None

    def get_domain_info(self, domain):
        conn = self._get_conn(); c = conn.cursor(); c.execute("SELECT status, last_check FROM status WHERE domain=?", (domain,)); row = c.fetchone(); conn.close()
        return (row[0], row[1]) if row else ("YENI", "--")

    def get_domain_status(self, domain):
        conn = self._get_conn(); c = conn.cursor(); c.execute("SELECT status FROM status WHERE domain=?", (domain,)); row = c.fetchone(); conn.close()
        return row[0] if row else "YENI"

    def update_domain_status(self, domain, status):
        with self._lock:
            conn = self._get_conn(); c = conn.cursor(); now = datetime.datetime.now().strftime("%d.%m %H:%M:%S")
            c.execute("INSERT OR REPLACE INTO status (domain, status, last_check) VALUES (?, ?, ?)", (domain, status, now)); conn.commit(); conn.close()

    def add_webhook(self, user_id: str, name: str, url: str, domains: list, days: int):
        with self._lock:
            conn = self._get_conn(); expiry = datetime.datetime.now() + datetime.timedelta(days=days)
            conn.execute("INSERT INTO webhooks (user_id, name, url, domains, expiry_date, active) VALUES (?, ?, ?, ?, ?, 1)", (str(user_id), name, url, ",".join(domains), str(expiry)))
            wid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.commit(); conn.close(); return wid

    def get_webhooks(self, user_id: str):
        conn = self._get_conn(); rows = conn.execute("SELECT id, name, url, domains, expiry_date, active FROM webhooks WHERE user_id=? ORDER BY id", (str(user_id),)).fetchall(); conn.close()
        return [{"id": r[0], "name": r[1], "url": r[2], "domains": r[3].split(",") if r[3] else [], "expiry_date": r[4], "active": bool(r[5])} for r in rows]

    def get_webhook(self, wid: int):
        conn = self._get_conn(); r = conn.execute("SELECT id, name, url, domains, expiry_date, active FROM webhooks WHERE id=?", (wid,)).fetchone(); conn.close()
        return {"id": r[0], "name": r[1], "url": r[2], "domains": r[3].split(",") if r[3] else [], "expiry_date": r[4], "active": bool(r[5])} if r else None

    def toggle_webhook(self, wid: int):
        with self._lock:
            conn = self._get_conn(); curr = conn.execute("SELECT active FROM webhooks WHERE id=?", (wid,)).fetchone()
            if curr: conn.execute("UPDATE webhooks SET active=? WHERE id=?", (0 if curr[0] else 1, wid))
            conn.commit(); conn.close()

    def delete_webhook(self, wid: int):
        with self._lock:
            conn = self._get_conn(); conn.execute("DELETE FROM webhooks WHERE id=?", (wid,)); conn.commit(); conn.close()

    def get_expiring_webhooks(self, hours=24):
        """24 saat içinde süresi dolacak webhookları getirir."""
        conn = self._get_conn()
        now = datetime.datetime.now()
        future = now + datetime.timedelta(hours=hours)
        
        rows = conn.execute("""
            SELECT id, user_id, name, url, expiry_date FROM webhooks 
            WHERE active=1 AND expiry_date > ? AND expiry_date <= ?
        """, (str(now), str(future))).fetchall()
        conn.close()
        
        return [{"id": r[0], "user_id": r[1], "name": r[2], "url": r[3], "expiry_date": r[4]} for r in rows]

    def get_expired_webhooks(self):
        """Süresi dolmuş aktif webhookları getirir."""
        conn = self._get_conn()
        now = str(datetime.datetime.now())
        
        rows = conn.execute("""
            SELECT id, user_id, name, url, expiry_date FROM webhooks 
            WHERE active=1 AND expiry_date < ?
        """, (now,)).fetchall()
        conn.close()
        
        return [{"id": r[0], "user_id": r[1], "name": r[2], "url": r[3], "expiry_date": r[4]} for r in rows]

    def deactivate_webhook(self, wid: int):
        """Webhook'u pasif yap."""
        with self._lock:
            conn = self._get_conn()
            conn.execute("UPDATE webhooks SET active=0 WHERE id=?", (wid,))
            conn.commit(); conn.close()

    def get_active_webhooks_for_domain(self, uid, dom):
        conn = self._get_conn()
        now = str(datetime.datetime.now())
        
        # Loglama ekliyoruz
        # print(f"DEBUG DB: Webhook aranıyor User: {uid}, Domain: {dom}, Time > {now}")
        
        rows = conn.execute("""
            SELECT id, url, domains, expiry_date, active 
            FROM webhooks 
            WHERE user_id=? AND active=1 AND expiry_date > ?
        """, (str(uid), now)).fetchall()
        
        conn.close()
        res = []
        
        for wid, url, dstr, exp, act in rows:
            webhook_domains = [d.strip() for d in (dstr or "").split(",")]
            # Wildcard veya tam eşleşme kontrolü
            if "*" in webhook_domains or dom in webhook_domains:
                res.append({"id": wid, "url": url})
            else:
                # print(f"DEBUG DB: Webhook ID {wid} elendi. Hedef: {webhook_domains}, Aranan: {dom}")
                pass
                
        return res

    def get_setting(self, key):
        conn = self._get_conn(); r = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone(); conn.close()
        return bool(r[0]) if r else True

    def toggle_setting(self, key):
        with self._lock:
            current = self.get_setting(key); new_val = 0 if current else 1
            conn = self._get_conn(); conn.execute("UPDATE settings SET value=? WHERE key=?", (new_val, key)); conn.commit(); conn.close()
            return bool(new_val)

    def update_stats(self, durum):
        with self._lock:
            conn = self._get_conn(); today = str(datetime.date.today())
            if not conn.execute("SELECT * FROM stats WHERE date=?", (today,)).fetchone(): conn.execute("INSERT INTO stats (date) VALUES (?)", (today,))
            col = "clean" if durum == "TEMİZ" else "banned" if durum == "ENGELLİ" else "error" if durum == "HATA" else None
            conn.execute("UPDATE stats SET total = total + 1 WHERE date=?", (today,))
            if col: conn.execute(f"UPDATE stats SET {col} = {col} + 1 WHERE date=?", (today,))
            conn.commit(); conn.close()

    def get_stats(self, date_str=None):
        conn = self._get_conn(); t = date_str if date_str else str(datetime.date.today())
        row = conn.execute("SELECT total, clean, banned, error FROM stats WHERE date=?", (t,)).fetchone(); conn.close()
        return {"date": t, "total": row[0], "TEMIZ": row[1], "ENGELLİ": row[2], "HATA": row[3]} if row else {"date": t, "total": 0, "TEMIZ": 0, "ENGELLİ": 0, "HATA": 0}

    def get_weekly_stats(self):
        conn = self._get_conn(); today = datetime.date.today(); week_ago = today - datetime.timedelta(days=7)
        row = conn.execute("SELECT SUM(total), SUM(clean), SUM(banned), SUM(error) FROM stats WHERE date >= ? AND date < ?", (str(week_ago), str(today))).fetchone(); conn.close()
        p = f"{week_ago.strftime('%d.%m')} - {(today - datetime.timedelta(days=1)).strftime('%d.%m')}"
        return {"period": p, "total": row[0], "TEMIZ": row[1], "ENGELLİ": row[2], "HATA": row[3]} if row and row[0] else {"period": p, "total": 0, "TEMIZ": 0, "ENGELLİ": 0, "HATA": 0}

    def ekle_domain(self, uid, dom):
        with self._lock:
            conn = self._get_conn(); 
            try: conn.execute("INSERT INTO domains (user_id, domain) VALUES (?, ?)", (str(uid), dom)); conn.commit(); return True
            except: return False
            finally: conn.close()

    def sil_domain(self, uid, dom):
        with self._lock:
            conn = self._get_conn(); c = conn.execute("DELETE FROM domains WHERE user_id=? AND domain=?", (str(uid), dom)); count = c.rowcount; conn.commit(); conn.close()
            return count > 0

    def get_user_domains(self, uid):
        conn = self._get_conn(); rows = conn.execute("SELECT domain FROM domains WHERE user_id=?", (str(uid),)).fetchall(); conn.close()
        return [r[0] for r in rows]

    def get_all_users_domains(self):
        """Tüm aktif kullanıcıların domainlerini getirir.
        Sadece süresi dolmamış kullanıcıların domainlerini döndürür (kaynak tasarrufu).
        """
        conn = self._get_conn()
        now = str(datetime.datetime.now())
        
        # Sadece süresi dolmamış kullanıcıların domainlerini al
        u_rows = conn.execute("""
            SELECT d.user_id, d.domain FROM domains d
            INNER JOIN users u ON d.user_id = u.user_id
            WHERE u.expiry_date > ? OR u.plan = 'admin'
        """, (now,)).fetchall()
        
        w_rows = conn.execute("SELECT user_id, domains FROM webhooks WHERE active=1 AND expiry_date > ?", (now,)).fetchall()
        conn.close()
        
        res = {}
        for u, d in u_rows:
            if u not in res: res[u] = []
            if d not in res[u]: res[u].append(d)
        for u, ds in w_rows:
            if not ds or "*" in ds: continue
            if u not in res: res[u] = []
            for d in [x.strip() for x in ds.split(",")]:
                if d and "." in d and d not in res[u]: res[u].append(d)
        return res

    def get_users_for_domain(self, domain):
        conn = self._get_conn()
        users = [r[0] for r in conn.execute("SELECT DISTINCT user_id FROM domains WHERE domain=?", (domain,)).fetchall()]
        # Webhook kullanıcılarını da ekle
        for uid, d_str in conn.execute("SELECT user_id, domains FROM webhooks WHERE active=1 AND expiry_date > ?", (str(datetime.datetime.now()),)).fetchall():
            if d_str and ("*" in d_str or domain in [d.strip() for d in d_str.split(",")]):
                if uid not in users: users.append(uid)
        conn.close()
        return users

    def update_webhook_domain_string(self, old, new):
        with self._lock:
            conn = self._get_conn(); cnt = 0
            for wid, dstr in conn.execute("SELECT id, domains FROM webhooks WHERE domains LIKE ?", (f"%{old}%",)).fetchall():
                if not dstr: continue
                lst = [d.strip() for d in dstr.split(",")]
                if old in lst:
                    nl = [new if x==old else x for x in lst]
                    conn.execute("UPDATE webhooks SET domains=? WHERE id=?", (",".join(nl), wid)); cnt += 1
            conn.commit(); conn.close(); return cnt

    def export_all_data(self):
        """
        Veritabanındaki tüm verileri detaylı, okunabilir bir rapor formatında dışa aktarır.
        """
        conn = self._get_conn()
        c = conn.cursor()
        output = []
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # --- BAŞLIK ---
        output.append(f"📊 VERİTABANI DETAYLI EXPORT RAPORU")
        output.append(f"📅 Rapor Tarihi: {now}")
        output.append("=" * 65)

        # --- 1. GENEL ÖZET İSTATİSTİKLER ---
        try:
            total_users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            total_domains = c.execute("SELECT COUNT(*) FROM domains").fetchone()[0]
            total_webhooks = c.execute("SELECT COUNT(*) FROM webhooks").fetchone()[0]
            
            # Domain durum sayıları
            clean_count = c.execute("SELECT COUNT(*) FROM status WHERE status='TEMİZ'").fetchone()[0]
            banned_count = c.execute("SELECT COUNT(*) FROM status WHERE status='ENGELLİ'").fetchone()[0]
            
            output.append("🔢 GENEL SİSTEM ÖZETİ")
            output.append(f"• Toplam Üye Sayısı    : {total_users}")
            output.append(f"• Toplam Takip Edilen  : {total_domains} Domain")
            output.append(f"• Tanımlı Webhook      : {total_webhooks}")
            output.append(f"• Durum Dağılımı       : {clean_count} TEMİZ | {banned_count} ENGELLİ")
            output.append("-" * 65)
        except Exception as e:
            output.append(f"❌ İstatistik Hatası: {e}")

        # --- 2. KULLANICI DETAYLARI ---
        output.append("\n👤 KULLANICI DETAYLARI VE PAKETLERİ")
        output.append(f"{'USER ID':<15} | {'USERNAME':<15} | {'PLAN':<10} | {'DOM':<3} | {'BAŞLANGIÇ':<16} | {'BİTİŞ':<16}")
        output.append("-" * 85)
        
        users = c.execute("SELECT user_id, plan, start_date, expiry_date, username FROM users ORDER BY expiry_date DESC").fetchall()
        
        for u in users:
            uid, plan, start, expiry, uname = u
            uname_str = f"@{uname}" if uname else "-"
            # Kullanıcıların kaç domaini var?
            d_count = c.execute("SELECT COUNT(*) FROM domains WHERE user_id=?", (uid,)).fetchone()[0]
            
            # Tarih formatlama (Sadece YYYY-MM-DD HH:MM kısmını al)
            s_date = start[:16] if start else "-"
            e_date = expiry[:16] if expiry else "-"
            
            output.append(f"{uid:<15} | {uname_str:<15} | {plan:<10} | {d_count:<3} | {s_date:<16} | {e_date:<16}")
        
            
            output.append(f"{uid:<15} | {uname_str:<15} | {plan:<10} | {d_count:<3} | {s_date:<16} | {e_date:<16}")
        
        output.append("=" * 65)

        # --- 3. WEBHOOK DETAYLARI ---
        output.append("\n🔗 TANIMLI WEBHOOKLAR")
        webhooks = c.execute("SELECT id, user_id, name, url, domains, expiry_date, active FROM webhooks").fetchall()
        
        if not webhooks:
            output.append("   (Sistemde kayıtlı webhook bulunmamaktadır.)")
        else:
            for w in webhooks:
                wid, owner, name, url, targets, exp, active = w
                status_simge = "🟢 AKTİF" if active else "🔴 PASİF"
                output.append(f"🔹 [ID: {wid}] {name} ({status_simge})")
                output.append(f"   ├─ Sahibi    : {owner}")
                output.append(f"   ├─ URL       : {url}")
                output.append(f"   ├─ Hedefler  : {targets}")
                output.append(f"   └─ Bitiş     : {exp}")
                output.append("")

        output.append("=" * 65)

        # --- 4. AYARLAR ---
        output.append("\n⚙️ SİSTEM AYARLARI (Settings Tablosu)")
        settings = c.execute("SELECT key, value FROM settings").fetchall()
        for k, v in settings:
            durum = "✅ AÇIK" if v else "❌ KAPALI"
            output.append(f"• {k:<20} : {durum}")

        output.append("=" * 65)

        # --- 5. DOMAIN LİSTESİ (GRUPLU) ---
        output.append("\n📄 KULLANICI BAZLI DOMAIN LİSTESİ")
        
        # Kullanıcıları ve domainlerini çek
        all_domains = c.execute("SELECT user_id, domain FROM domains ORDER BY user_id").fetchall()
        
        if not all_domains:
            output.append("   (Hiç domain eklenmemiş.)")
        else:
            current_user = None
            for row in all_domains:
                uid, domain = row
                
                # Yeni kullanıcı başlığı
                if uid != current_user:
                    output.append(f"\n🔻 Kullanıcı: {uid}")
                    current_user = uid
                
                # Domainin durumunu da çekelim ki tam liste olsun
                status_row = c.execute("SELECT status FROM status WHERE domain=?", (domain,)).fetchone()
                status_str = status_row[0] if status_row else "BİLİNMİYOR"
                
                # Liste elemanı
                icon = "✅" if status_str == "TEMİZ" else "🚫" if status_str == "ENGELLİ" else "⚠️"
                output.append(f"   └─ {domain:<25} {icon} {status_str}")

        conn.close()
        return "\n".join(output)

    # --- REFERANS SİSTEMİ ---
    
    def add_referral(self, referrer_id: str, referred_id: str) -> bool:
        """Yeni referans kaydı ekle"""
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "INSERT INTO referrals (referrer_id, referred_id, status, created_at) VALUES (?, ?, 'pending', ?)",
                    (str(referrer_id), str(referred_id), str(datetime.datetime.now()))
                )
                conn.commit()
                return True
            except:
                return False  # Zaten kayıtlı
            finally:
                conn.close()
    
    def get_referrer(self, referred_id: str) -> str:
        """Kullanıcıyı davet eden kişiyi bul"""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT referrer_id FROM referrals WHERE referred_id = ?",
            (str(referred_id),)
        ).fetchone()
        conn.close()
        return row[0] if row else None
    
    def process_referral_reward(self, referred_id: str, bonus_days: int = 7) -> dict:
        """Referans ödülünü işle - davet edene bonus gün ekle"""
        with self._lock:
            conn = self._get_conn()
            c = conn.cursor()
            
            # Referans kaydını bul
            row = c.execute(
                "SELECT referrer_id, status FROM referrals WHERE referred_id = ?",
                (str(referred_id),)
            ).fetchone()
            
            if not row:
                conn.close()
                return {"success": False, "error": "Referans kaydı bulunamadı"}
            
            referrer_id, status = row
            
            if status == "completed":
                conn.close()
                return {"success": False, "error": "Ödül zaten verildi"}
            
            # Davet edenin süresini uzat
            user_row = c.execute(
                "SELECT expiry_date FROM users WHERE user_id = ?",
                (referrer_id,)
            ).fetchone()
            
            if user_row and user_row[0]:
                try:
                    current_expiry = datetime.datetime.strptime(user_row[0][:19], "%Y-%m-%d %H:%M:%S")
                    now = datetime.datetime.now()
                    
                    if current_expiry > now:
                        new_expiry = current_expiry + datetime.timedelta(days=bonus_days)
                    else:
                        new_expiry = now + datetime.timedelta(days=bonus_days)
                    
                    c.execute(
                        "UPDATE users SET expiry_date = ? WHERE user_id = ?",
                        (str(new_expiry), referrer_id)
                    )
                except:
                    conn.close()
                    return {"success": False, "error": "Tarih işleme hatası"}
            
            # Referans kaydını güncelle
            c.execute(
                "UPDATE referrals SET status = 'completed', reward_days = ? WHERE referred_id = ?",
                (bonus_days, str(referred_id))
            )
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "referrer_id": referrer_id,
                "bonus_days": bonus_days
            }
    
    def give_immediate_referral_bonus(self, referrer_id: str, bonus_hours: int = 24) -> bool:
        """Referans linki ile birisi katıldığında davet edene anında bonus ver"""
        with self._lock:
            conn = self._get_conn()
            c = conn.cursor()
            
            try:
                # Davet edenin mevcut süresini al
                row = c.execute(
                    "SELECT expiry_date FROM users WHERE user_id = ?",
                    (str(referrer_id),)
                ).fetchone()
                
                if row and row[0]:
                    current_expiry = datetime.datetime.strptime(row[0][:19], "%Y-%m-%d %H:%M:%S")
                    now = datetime.datetime.now()
                    
                    # Mevcut süre aktifse üzerine ekle, değilse şimdiden başlat
                    if current_expiry > now:
                        new_expiry = current_expiry + datetime.timedelta(hours=bonus_hours)
                    else:
                        new_expiry = now + datetime.timedelta(hours=bonus_hours)
                    
                    c.execute(
                        "UPDATE users SET expiry_date = ? WHERE user_id = ?",
                        (str(new_expiry), str(referrer_id))
                    )
                    conn.commit()
                    return True
            except Exception as e:
                print(f"Referral bonus error: {e}")
                return False
            finally:
                conn.close()
        return False

    def get_referral_stats(self, user_id: str) -> dict:
        """Kullanıcının referans istatistiklerini getir"""
        conn = self._get_conn()
        
        # Toplam davet
        total = conn.execute(
            "SELECT COUNT(*) FROM referrals WHERE referrer_id = ?",
            (str(user_id),)
        ).fetchone()[0]
        
        # Ödeme yapanlar (completed)
        completed = conn.execute(
            "SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND status = 'completed'",
            (str(user_id),)
        ).fetchone()[0]
        
        # Toplam kazanılan gün
        total_days = conn.execute(
            "SELECT COALESCE(SUM(reward_days), 0) FROM referrals WHERE referrer_id = ? AND status = 'completed'",
            (str(user_id),)
        ).fetchone()[0]
        
        conn.close()
        
        return {
            "total_referrals": total,
            "completed": completed,
            "pending": total - completed,
            "total_bonus_days": total_days
        }

    
    def update_username(self, user_id: str, username: str):
        """Kullanıcının username bilgisini günceller"""
        if not username: return
        with self._lock:
            conn = self._get_conn()
            try:
                # Sadece mevcut kullanıcı varsa güncelle
                conn.execute("UPDATE users SET username=? WHERE user_id=?", (username, str(user_id)))
                conn.commit()
            except: pass
            finally: conn.close()
            
    def get_all_users_with_details(self):
        """Kullanıcı listesi komutu için detaylı veri"""
        conn = self._get_conn()
        rows = conn.execute("SELECT user_id, username, plan, expiry_date FROM users ORDER BY expiry_date DESC").fetchall()
        conn.close()
        return [{"user_id": r[0], "username": r[1], "plan": r[2], "expiry_date": r[3]} for r in rows]

    def create_notification_key(self, user_id: str, domain: str) -> str:
        """Domain için yeni bir bildirim anahtarı oluşturur"""
        import uuid
        key = f"KEY-{str(uuid.uuid4())[:8].upper()}"
        with self._lock:
            conn = self._get_conn()
            # Varsa eskisini sil (veya birden fazla key izin verilebilir ama şimdilik tek key basit tutalım)
            conn.execute("DELETE FROM notification_links WHERE domain=? AND owner_id=? AND linked_chat_id IS NULL", (domain, str(user_id)))
            conn.execute("INSERT INTO notification_links (key, domain, owner_id) VALUES (?, ?, ?)", (key, domain, str(user_id)))
            conn.commit(); conn.close()
        return key

    def link_chat_to_key(self, key: str, chat_id: str) -> dict:
        """Anahtarı kullanarak grubu domaine bağlar"""
        with self._lock:
            conn = self._get_conn()
            c = conn.cursor()
            row = c.execute("SELECT domain, owner_id, linked_chat_id FROM notification_links WHERE key=?", (key,)).fetchone()
            
            if not row:
                conn.close()
                return {"success": False, "msg": "❌ Geçersiz veya silinmiş anahtar."}
            
            domain, owner, current_link = row
            
            # Anahtar zaten kullanılmış mı? (İstenirse tek kullanımlık yapılabilir, şimdilik kalıcı)
            # Eğer anahtar tek bir grubu bağlıyorsa UPDATE yapalım.
            
            c.execute("UPDATE notification_links SET linked_chat_id=? WHERE key=?", (str(chat_id), key))
            conn.commit(); conn.close()
            return {"success": True, "domain": domain}

    def get_linked_chats_for_domain(self, domain: str) -> list:
        """Domain'e bağlı ek chat ID'leri getirir"""
        conn = self._get_conn()
        rows = conn.execute("SELECT linked_chat_id FROM notification_links WHERE domain=? AND linked_chat_id IS NOT NULL", (domain,)).fetchall()
        conn.close()
        # Unique list yap
        return list(set([r[0] for r in rows]))
    
    def get_linked_domains_for_chat(self, chat_id: str) -> list:
        """Bir Chat ID'ye (grup) bağlı domainleri getirir"""
        conn = self._get_conn()
        rows = conn.execute("SELECT domain FROM notification_links WHERE linked_chat_id=?", (str(chat_id),)).fetchall()
        conn.close()
        return [r[0] for r in rows]
