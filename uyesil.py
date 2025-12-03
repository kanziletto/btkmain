import sqlite3
import os

DB_FILE = "bot_data.db"

def delete_user(user_id):
    if not os.path.exists(DB_FILE):
        print(f"❌ Hata: {DB_FILE} bulunamadı!")
        return

    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        # 1. Kullanıcının varlığını kontrol et
        c.execute("SELECT * FROM users WHERE user_id=?", (str(user_id),))
        if not c.fetchone():
            print(f"⚠️ Kullanıcı bulunamadı: {user_id}")
            conn.close()
            return

        print(f"🚨 {user_id} ID'li kullanıcı ve tüm verileri silinecek. Emin misiniz? (E/H)")
        confirm = input("> ")
        
        if confirm.lower() != 'e':
            print("❌ İşlem iptal edildi.")
            conn.close()
            return

        # 2. Kullanıcıya ait verileri sil
        # Domains tablosundan sil
        c.execute("DELETE FROM domains WHERE user_id=?", (str(user_id),))
        domains_deleted = c.rowcount
        
        # Webhooks tablosundan sil
        c.execute("DELETE FROM webhooks WHERE user_id=?", (str(user_id),))
        webhooks_deleted = c.rowcount
        
        # Users tablosundan sil
        c.execute("DELETE FROM users WHERE user_id=?", (str(user_id),))
        users_deleted = c.rowcount

        conn.commit()
        conn.close()

        print("-" * 30)
        print("✅ KULLANICI BAŞARIYLA SİLİNDİ")
        print("-" * 30)
        print(f"👤 Silinen Kullanıcı: {users_deleted}")
        print(f"🌐 Silinen Domainler: {domains_deleted}")
        print(f"🔗 Silinen Webhooklar: {webhooks_deleted}")
        print("-" * 30)

    except Exception as e:
        print(f"❌ Bir hata oluştu: {e}")

if __name__ == "__main__":
    print("🗑️ ÜYE SİLME ARACI")
    target_id = input("Silinecek Telegram User ID: ")
    delete_user(target_id)
