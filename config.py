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
DB_FILE = "bot_data.db"
LOG_DIR = "logs"
MAX_CONCURRENT_SCANS = 2

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
