import logging
import colorlog
from dataclasses import dataclass, field
from typing import List, Optional

def setup_logger():
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s[%(asctime)s] %(message)s',
        datefmt='%H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    ))
    logger = colorlog.getLogger('BTKBot')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

logger = setup_logger()

@dataclass
class SorguSonucu:
    domain: str
    durum: str
    detay: str
    sure: float
    captcha_text: Optional[str] = None
    screenshot_paths: List[str] = field(default_factory=list)
