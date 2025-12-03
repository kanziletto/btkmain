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
                         ultra_enabled INTEGER DEFAULT 1
                         )''')
            
            try: c.execute("ALTER TABLE users ADD COLUMN ultra_enabled INTEGER DEFAULT 1")
            except: pass

            c.execute('''CREATE TABLE IF NOT EXISTS domains (
                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                         user_id TEXT,
                         domain TEXT,
                         UNIQUE(user_id, domain)
                         )''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS status (domain TEXT PRIMARY KEY, status TEXT, last_check TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS stats (date TEXT PRIMARY KEY, total INTEGER DEFAULT 0, clean INTEGER DEFAULT 0, banned INTEGER DEFAULT 0, error INTEGER DEFAULT 0)''')
            c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value INTEGER)''')
            c.execute('''CREATE TABLE IF NOT EXISTS webhooks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, name TEXT, url TEXT, domains TEXT, expiry_date TEXT, active INTEGER DEFAULT 1)''')

            c.execute("SELECT * FROM users WHERE user_id=?", (str(ADMIN_ID),))
            if not c.fetchone():
                now = str(datetime.datetime.now())
                c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", (str(ADMIN_ID), "admin", now, "2099-12-31 23:59:59", 0, 1))

            defaults = [("silent_mode", 1), ("auto_switch", 1), ("system_active", 1), ("ultra_screenshots", 1)]
            for key, val in defaults:
                c.execute("INSERT OR IGNORE INTO settings VALUES (?, ?)", (key, val))

            conn.commit()
            conn.close()

    def register_user(self, user_id: str):
        with self._lock:
            conn = self._get_conn(); c = conn.cursor()
            if c.execute("SELECT * FROM users WHERE user_id=?", (str(user_id),)).fetchone(): conn.close(); return False
            now = datetime.datetime.now(); expiry = now + datetime.timedelta(days=2)
            c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", (str(user_id), "trial", str(now), str(expiry), 0, 1))
            conn.commit(); conn.close(); return True

    def register_user_scheduled(self, user_id: str, start_monday=False):
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
            c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", (str(user_id), "trial", str(start), str(expiry), 0, 1))
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
        if row: return {"plan": row[1], "start_date": row[2], "expiry_date": row[3], "ultra_enabled": bool(row[5]) if len(row)>5 else True}
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

    def set_premium(self, user_id: str, days: int):
        with self._lock:
            conn = self._get_conn(); now = datetime.datetime.now(); expiry = now + datetime.timedelta(days=days)
            conn.execute("INSERT OR REPLACE INTO users (user_id, plan, start_date, expiry_date, notified_expiry, ultra_enabled) VALUES (?, ?, ?, ?, ?, ?)", (str(user_id), "premium", str(now), str(expiry), 0, 1))
            conn.commit(); conn.close(); return str(expiry)

    def set_ultra(self, user_id: str, days: int):
        with self._lock:
            conn = self._get_conn(); now = datetime.datetime.now(); expiry = now + datetime.timedelta(days=days)
            conn.execute("INSERT OR REPLACE INTO users (user_id, plan, start_date, expiry_date, notified_expiry, ultra_enabled) VALUES (?, ?, ?, ?, ?, ?)", (str(user_id), "ultra", str(now), str(expiry), 0, 1))
            conn.commit(); conn.close(); return str(expiry)

    def get_domain_info(self, domain):
        conn = self._get_conn(); c = conn.cursor(); c.execute("SELECT status, last_check FROM status WHERE domain=?", (domain,)); row = c.fetchone(); conn.close()
        return (row[0], row[1]) if row else ("YENI", "--:--:--")

    def get_domain_status(self, domain):
        conn = self._get_conn(); c = conn.cursor(); c.execute("SELECT status FROM status WHERE domain=?", (domain,)); row = c.fetchone(); conn.close()
        return row[0] if row else "YENI"

    def update_domain_status(self, domain, status):
        with self._lock:
            conn = self._get_conn(); c = conn.cursor(); now = datetime.datetime.now().strftime("%H:%M:%S")
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
        conn = self._get_conn(); u_rows = conn.execute("SELECT user_id, domain FROM domains").fetchall()
        w_rows = conn.execute("SELECT user_id, domains FROM webhooks WHERE active=1 AND expiry_date > ?", (str(datetime.datetime.now()),)).fetchall(); conn.close()
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
        conn = self._get_conn(); c = conn.cursor()
        output = ["VERİTABANI EXPORT"]
        c.execute("SELECT user_id, plan FROM users"); output.append("KULLANICILAR:\n" + "\n".join([str(r) for r in c.fetchall()]))
        c.execute("SELECT user_id, domain FROM domains"); output.append("\nDOMAINLER:\n" + "\n".join([str(r) for r in c.fetchall()]))
        conn.close(); return "\n".join(output)
