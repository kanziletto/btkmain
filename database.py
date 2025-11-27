import json
import os
from typing import List, Dict
from config import DB_FILE

class Database:
    def __init__(self):
        self.file_path = DB_FILE
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump({}, f)

    def _load(self) -> Dict:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    def _save(self, data: Dict):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def ekle_domain(self, chat_id: str, domain: str) -> bool:
        data = self._load()
        chat_id = str(chat_id)
        if chat_id not in data:
            data[chat_id] = []
        
        if domain not in data[chat_id]:
            data[chat_id].append(domain)
            self._save(data)
            return True
        return False

    def sil_domain(self, chat_id: str, domain: str) -> bool:
        data = self._load()
        chat_id = str(chat_id)
        if chat_id in data and domain in data[chat_id]:
            data[chat_id].remove(domain)
            self._save(data)
            return True
        return False

    def get_all_users_domains(self) -> Dict[str, List[str]]:
        return self._load()

    def get_user_domains(self, chat_id: str) -> List[str]:
        data = self._load()
        return data.get(str(chat_id), [])
