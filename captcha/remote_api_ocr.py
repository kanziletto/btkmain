from .base import BaseCaptchaSolver
import requests
from utils import logger
from config import OCR_API_URL
import io

class RemoteAPISolver(BaseCaptchaSolver):
    def __init__(self):
        self.api_url = OCR_API_URL

    def solve(self, image_data) -> str:
        """
        image_data: Dosya yolu (str) VEYA Resim verisi (bytes) olabilir.
        """
        try:
            files = None
            opened_file = None

            # Eğer gelen veri dosya yolu ise (str), dosyayı aç
            if isinstance(image_data, str):
                opened_file = open(image_data, 'rb')
                files = {'file': ('captcha.png', opened_file, 'image/png')}
            
            # Eğer gelen veri zaten resim ise (bytes/BytesIO)
            elif isinstance(image_data, (bytes, io.BytesIO)):
                if isinstance(image_data, io.BytesIO):
                    image_data.seek(0) # Başa sar
                files = {'file': ('captcha.png', image_data, 'image/png')}

            # Timeout süresini 10 saniyeye düşürdük (30sn çok uzun)
            response = requests.post(self.api_url, files=files, timeout=10)
            
            # Eğer dosya açtıysak kapatalım
            if opened_file:
                opened_file.close()
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    return result.get("text", "")
            return ""

        except Exception as e:
            logger.error(f"API Hatası ({self.api_url}): {e}")
            return ""
