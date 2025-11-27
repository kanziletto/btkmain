from typing import List
from .remote_api_ocr import RemoteAPISolver 
from utils import logger

class CaptchaManager:
    def __init__(self, providers: List[str]):
        self.solvers = {}
        self.priority_list = providers
        
        if 'remote_api' in providers:
            self.solvers['remote_api'] = RemoteAPISolver()
            
    def solve(self, image_path: str) -> tuple[str, str]:
        errors = []
        for provider_name in self.priority_list:
            solver = self.solvers.get(provider_name)
            if not solver: continue
            try:
                text = solver.solve(image_path)
                if text and len(text.strip()) > 2:
                    return text.strip(), provider_name
                else:
                    errors.append(f"{provider_name}: Sonuç boş")
            except Exception as e:
                errors.append(f"{provider_name}: {str(e)}")
        logger.error(f"TÜM YÖNTEMLER BAŞARISIZ: {errors}")
        return "00000", "failed"
