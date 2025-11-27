from abc import ABC, abstractmethod

class BaseCaptchaSolver(ABC):
    @abstractmethod
    def solve(self, image_path: str) -> str:
        """Görüntü yolunu alır, metni döndürür."""
        pass
