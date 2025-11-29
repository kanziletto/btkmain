import sqlite3
import datetime
import os
import threading
from dateutil.parser import parse
from config import ADMIN_ID

DB_FILE_SQL = "bot_data.db"

class Database:
    def __init__(self):
        self.db_path = DB_FILE_SQL
        self._lock = threading.Lock()
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self):
        """Tabloları oluşturur"""
        with self._lock:
            conn = self._get_conn()
            c = conn.cursor()
            
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                         user_id TEXT PRIMARY KEY,
                         plan TEXT,
                         start_date TEXT,
                         expiry_date TEXT,
                         notified_expiry INTEGER DEFAULT 0
                         )''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS domains (
                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                         user_id TEXT,
                         domain TEXT,
                         UNIQUE(user_id, domain)
                         )''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS status (
                         domain TEXT PRIMARY KEY,
                         status TEXT,
                         last_check TEXT
                         )''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS stats (
                         date TEXT PRIMARY KEY,
                         total INTEGER DEFAULT 0,
                         clean INTEGER DEFAULT 0,
                         banned INTEGER DEFAULT 0,
                         error INTEGER DEFAULT 0
                         )''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS settings (
                         key TEXT PRIMARY KEY,
                         value INTEGER
                         )''')

            c.execute("SELECT * FROM users WHERE user_id=?", (str(ADMIN_ID),))
            if not c.fetchone():
                now = str(datetime.datetime.now())
                expiry = "2099-12-31 23:59:59"
                c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", 
                          (str(ADMIN_ID), "admin", now, expiry, 0))

            defaults = [("silent_mode", 1), ("auto_switch", 1), ("system_active", 1)]
            for key, val in defaults:
                c.execute("INSERT OR IGNORE INTO settings VALUES (?, ?)", (key, val))

            conn.commit()
            conn.close()

    def register_user(self, user_id: str):
        with self._lock:
            conn = self._get_conn()
            c = conn.cursor()
            user_id = str(user_id)
            
            c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
            if c.fetchone():
                conn.close()
                return False
            
            now = datetime.datetime.now()
            expiry = now + datetime.timedelta(days=2)
            
            c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", 
                      (user_id, "trial", str(now), str(expiry), 0))
            conn.commit()
            conn.close()
            return True

    def register_user_scheduled(self, user_id: str, start_monday=False):
        """
        Kullanıcı kaydını oluşturur.
        start_monday=True ise trial en yakın Pazartesi 08:00'da başlar.
        """
        with self._lock:
            conn = self._get_conn()
            c = conn.cursor()
            user_id = str(user_id)
            
            c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
            if c.fetchone():
                conn.close()
                return False, None, None  # Zaten var
            
            now = datetime.datetime.now()
            
            if start_monday:
                # En yakın Pazartesi 08:00'ı bul
                days_until_monday = (7 - now.weekday()) % 7
                if days_until_monday == 0 and now.hour >= 8:
                    days_until_monday = 7  # Bugün Pazartesi ve saat 08:00 geçti, gelecek Pazartesi
                
                start_date = now + datetime.timedelta(days=days_until_monday)
                start_date = start_date.replace(hour=8, minute=0, second=0, microsecond=0)
            else:
                # Hemen başlat
                start_date = now
            
            expiry = start_date + datetime.timedelta(hours=48)  # 48 saat
            
            c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", 
                      (user_id, "trial", str(start_date), str(expiry), 0))
            conn.commit()
            conn.close()
            
            return True, start_date, expiry

    def get_next_monday_8am(self):
        """En yakın Pazartesi 08:00'ı döndürür"""
        now = datetime.datetime.now()
        days_until_monday = (7 - now.weekday()) % 7
        
        if days_until_monday == 0 and now.hour >= 8:
            days_until_monday = 7
        
        monday = now + datetime.timedelta(days=days_until_monday)
        return monday.replace(hour=8, minute=0, second=0, microsecond=0)

    def check_user_access(self, user_id: str) -> dict:
        user_id = str(user_id)
        if user_id == str(ADMIN_ID):
            return {"access": True, "plan": "admin", "msg": "Admin"}

        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT plan, start_date, expiry_date FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        conn.close()

        if not row:
            return {"access": False, "plan": "none", "msg": "Kayıt bulunamadı. /start yazın."}

        plan, start_str, expiry_str = row
        
        try:
            start_date = parse(start_str)
            expiry = parse(expiry_str)
            now = datetime.datetime.now()
            
            # Eğer başlangıç tarihi gelecekte ise henüz aktif değil
            if now < start_date:
                return {"access": False, "plan": "scheduled", "msg": f"⏳ Paketiniz {start_date.strftime('%d.%m.%Y %H:%M')}'de başlayacak."}
            
            # Süre kontrolü
            if now > expiry:
                return {"access": False, "plan": "expired", "msg": "⏳ Süreniz doldu."}
        except:
            return {"access": False, "plan": "error", "msg": "Tarih hatası."}

        return {"access": True, "plan": plan, "msg": "Aktif"}

    def get_user_data(self, user_id):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id=?", (str(user_id),))
        row = c.fetchone()
        conn.close()
        if row:
            return {"plan": row[1], "start_date": row[2], "expiry_date": row[3]}
        return {}

    def get_expired_users_to_notify(self):
        conn = self._get_conn()
        c = conn.cursor()
        now = str(datetime.datetime.now())
        c.execute("SELECT user_id FROM users WHERE expiry_date < ? AND notified_expiry = 0 AND plan != 'admin'", (now,))
        rows = c.fetchall()
        conn.close()
        return [r[0] for r in rows]

    def mark_user_notified(self, user_id: str):
        with self._lock:
            conn = self._get_conn()
            c = conn.cursor()
            c.execute("UPDATE users SET notified_expiry = 1 WHERE user_id=?", (str(user_id),))
            conn.commit()
            conn.close()

    def set_premium(self, user_id: str, days: int):
        with self._lock:
            conn = self._get_conn()
            c = conn.cursor()
            now = datetime.datetime.now()
            expiry = now + datetime.timedelta(days=days)
            
            c.execute("""INSERT OR REPLACE INTO users (user_id, plan, start_date, expiry_date, notified_expiry) 
                         VALUES (?, ?, ?, ?, ?)""", 
                      (str(user_id), "premium", str(now), str(expiry), 0))
            
            conn.commit()
            conn.close()
            return str(expiry)

    def get_setting(self, key):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = c.fetchone()
        conn.close()
        return bool(row[0]) if row else True

    def toggle_setting(self, key):
        with self._lock:
            current = self.get_setting(key)
            new_val = 0 if current else 1
            conn = self._get_conn()
            c = conn.cursor()
            c.execute("UPDATE settings SET value=? WHERE key=?", (new_val, key))
            conn.commit()
            conn.close()
            return bool(new_val)

    def update_stats(self, durum):
        with self._lock:
            conn = self._get_conn()
            c = conn.cursor()
            today = str(datetime.date.today())
            
            c.execute("SELECT * FROM stats WHERE date=?", (today,))
            if not c.fetchone():
                c.execute("INSERT INTO stats (date) VALUES (?)", (today,))
            
            c.execute("UPDATE stats SET total = total + 1 WHERE date=?", (today,))
            
            col = "clean" if durum == "TEMİZ" else "banned" if durum == "ENGELLİ" else "error" if durum == "HATA" else None
            if col:
                c.execute(f"UPDATE stats SET {col} = {col} + 1 WHERE date=?", (today,))
                
            conn.commit()
            conn.close()

    def get_stats(self):
        conn = self._get_conn()
        c = conn.cursor()
        today = str(datetime.date.today())
        c.execute("SELECT total, clean, banned, error FROM stats WHERE date=?", (today,))
        row = c.fetchone()
        conn.close()
        
        if row:
            return {"date": today, "total": row[0], "TEMIZ": row[1], "ENGELLİ": row[2], "HATA": row[3]}
        return {"date": today, "total": 0, "TEMIZ": 0, "ENGELLİ": 0, "HATA": 0}

    def get_domain_status(self, domain):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT status FROM status WHERE domain=?", (domain,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else "YENI"

    def get_domain_info(self, domain):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT status, last_check FROM status WHERE domain=?", (domain,))
        row = c.fetchone()
        conn.close()
        if row: return row[0], row[1]
        return "YENI", "--:--:--"

    def update_domain_status(self, domain, status):
        with self._lock:
            conn = self._get_conn()
            c = conn.cursor()
            now = datetime.datetime.now().strftime("%H:%M:%S")
            c.execute("INSERT OR REPLACE INTO status (domain, status, last_check) VALUES (?, ?, ?)", (domain, status, now))
            conn.commit()
            conn.close()

    def ekle_domain(self, chat_id, domain):
        with self._lock:
            conn = self._get_conn()
            c = conn.cursor()
            try:
                c.execute("INSERT INTO domains (user_id, domain) VALUES (?, ?)", (str(chat_id), domain))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
            finally:
                conn.close()

    def sil_domain(self, chat_id, domain):
        with self._lock:
            conn = self._get_conn()
            c = conn.cursor()
            c.execute("DELETE FROM domains WHERE user_id=? AND domain=?", (str(chat_id), domain))
            rows = c.rowcount
            conn.commit()
            conn.close()
            return rows > 0

    def get_user_domains(self, chat_id):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT domain FROM domains WHERE user_id=?", (str(chat_id),))
        rows = c.fetchall()
        conn.close()
        return [r[0] for r in rows]

    def get_all_users_domains(self):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT user_id, domain FROM domains")
        rows = c.fetchall()
        conn.close()
        
        result = {}
        for uid, dom in rows:
            if uid not in result: result[uid] = []
            result[uid].append(dom)
        return result
