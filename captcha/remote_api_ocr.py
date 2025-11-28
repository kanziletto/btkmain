from .base import BaseCaptchaSolver
import requests
from utils import logger
from config import OCR_API_URL # Config'den URL'i alıyoruz

class RemoteAPISolver(BaseCaptchaSolver):
    def __init__(self):
        # URL artık config.py dosyasından geliyor
        self.api_url = OCR_API_URL

    def solve(self, image_path: str) -> str:
        try:
            # Resmi diskten oku ve API'ye gönder
            with open(image_path, 'rb') as f:
                files = {'file': f}
                # Timeout süresini 5 saniye olarak koruyoruz
                response = requests.post(self.api_url, files=files, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    return result.get("text", "")
            return ""
        except Exception as e:
            logger.error(f"API Hatası ({self.api_url}): {e}")
            return ""
