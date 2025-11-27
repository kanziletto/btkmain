from .base import BaseCaptchaSolver
import requests
from utils import logger

class RemoteAPISolver(BaseCaptchaSolver):
    def __init__(self):
        # BURAYA DİĞER SUNUCUNUN IP ADRESİNİ YAZIN
        # Örnek: "http://10.0.0.5:8000/ocr"
        self.api_url = "http://10.0.0.87:8000/ocr" 

    def solve(self, image_path: str) -> str:
        try:
            with open(image_path, 'rb') as f:
                files = {'file': f}
                # Timeout 5 saniye (Aynı ağda oldukları için çok hızlıdır)
                response = requests.post(self.api_url, files=files, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    return result.get("text", "")
            return ""
        except Exception as e:
            logger.error(f"API Hatası: {e}")
            return ""
