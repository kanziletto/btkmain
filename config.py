# config.py
import os
import random

# Tokenleriniz
BOT_TOKEN = "8280880523:AAEu2wBiuix0PUNxHKIHuGmEPcArBENBTWo"
ADMIN_ID = 123456789

# --- TEK VE NET SEÇİM ---
CAPTCHA_PROVIDERS = ['remote_api'] 

# Selenium
HEADLESS_MODE = True

# Proxy Listeniz (Aynen kalsın)
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

# Yollar
DB_FILE = "domains.json"
LOG_DIR = "logs"
