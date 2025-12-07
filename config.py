import os
import random

# --- KİMLİK BİLGİLERİ ---
BOT_TOKEN = "8280880523:AAHa1jdL_JKZa1YqLr063Qp6VGOLFU2W7QQ"
ADMIN_ID = 7107697888
ADMIN_CHANNEL_ID = -1003498419781
SUPPORT_URL = "https://t.me/londonlondon25"

# --- SUNUCU AYARLARI ---
# OCR ve Resim Upload Sunucusu (Server 2)
# Not: Buraya 2. sunucunuzun PUBLIC IP adresini yazın
OCR_API_URL = "http://10.0.0.87:8000/ocr"
IMAGE_UPLOAD_URL = "http://79.76.116.181:8000/upload"

# --- DİĞER AYARLAR ---
CAPTCHA_PROVIDERS = ['remote_api'] 
HEADLESS_MODE = True
DB_FILE = "/home/ubuntu/btk/bot_data.db"
LOG_DIR = "logs"
MAX_CONCURRENT_SCANS = 2

# --- TRONSCAN ÖDEME SİSTEMİ ---
# Kendi USDT (TRC20) cüzdan adresinizi yazın
USDT_WALLET_ADDRESS = "TKGb3inpTMGvuLojp8dek4UXBASEN67wfa"

# TronScan API (opsiyonel - rate limit için)
TRONSCAN_API_KEY = "32a7d02e-118d-433c-ac40-f03627cb0ca6"

# USDT TRC20 Contract Adresi (değiştirmeyin)
USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

# Ödeme kontrolü için tolerans (dolar cinsinden)
PAYMENT_TOLERANCE = 0.10  # $0.10 tolerans

# Abonelik Paketleri - Yeni Yapı
# Tek paket: $60/ay
# Süreye göre domain artışı ve özellikler

# Gizli paket (admin tarafından verilir, satılmaz)
HIDDEN_ULTRA_TIER = {
    "name": "Ultra", 
    "base_price": 0, 
    "domains": 20, 
    "features": ["auto_scan", "notifications", "manual_query", "webhook", "screenshots"]
}

# Satışa açık paket süreleri
SUBSCRIPTION_DURATIONS = {
    "1m": {
        "label": "1 Ay", 
        "days": 30, 
        "price": 60, 
        "domains": 5, 
        "features": ["auto_scan", "notifications", "manual_query"]
    },
    "3m": {
        "label": "3 Ay", 
        "days": 90, 
        "price": 160,  # $53/ay
        "domains": 10, 
        "features": ["auto_scan", "notifications", "manual_query"]
    },
    "6m": {
        "label": "6 Ay", 
        "days": 180, 
        "price": 300,  # $50/ay
        "domains": 15, 
        "features": ["auto_scan", "notifications", "manual_query", "integration"]
    },
    "12m": {
        "label": "12 Ay", 
        "days": 365, 
        "price": 500,  # $42/ay
        "domains": 25, 
        "features": ["auto_scan", "notifications", "manual_query", "integration"]
    }
}

def get_plan_price(duration: str) -> dict:
    """Paket fiyatı hesapla"""
    d = SUBSCRIPTION_DURATIONS.get(duration)
    if not d:
        return None
    return {
        "name": f"Standart ({d['label']})",
        "price": d["price"],
        "currency": "USDT",
        "days": d["days"],
        "domains": d["domains"],
        "features": d["features"],
        "tier": "standard",
        "duration": duration
    }

# Geriye dönük uyumluluk için SUBSCRIPTION_PLANS
SUBSCRIPTION_PLANS = {
    f"standard_{dur}": get_plan_price(dur)
    for dur in SUBSCRIPTION_DURATIONS
}

# --- PROXY LİSTESİ ---
PROXY_LIST = [
    "212.135.181.42:6224", "195.40.186.107:5789", "195.40.186.41:5723",
    "108.165.227.66:5307", "108.165.227.77:5318", "23.26.231.88:7329",
    "23.26.231.109:7350", "212.135.180.74:6756", "212.135.181.239:6421",
    "108.165.161.51:5792", "50.114.243.229:6470", "108.165.227.82:5323",
    "212.135.180.25:6707", "50.114.243.110:6351", "50.114.243.83:6324",
    "23.26.231.135:7376", "50.114.243.54:6295", "195.40.186.83:5765",
    "195.40.187.153:5335", "108.165.161.178:5919", "195.40.186.249:5931",
    "23.26.231.163:7404", "50.114.243.176:6417", "212.135.180.177:6859",
    "50.114.243.163:6404", "212.135.180.123:6805"
]

def get_random_proxy():
    if not PROXY_LIST: return None
    proxy = random.choice(PROXY_LIST)
    if not proxy.startswith("http"):
        return f"http://{proxy}"
    return proxy
