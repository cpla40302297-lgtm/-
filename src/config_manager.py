"""
설정 관리 모듈 - 앱 키, 토큰, 게시물 템플릿 저장/불러오기
"""
import json
import os
from typing import Optional


CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")


DEFAULT_CONFIG = {
    "client_id": "",
    "client_secret": "",
    "access_token": "",
    "last_band_key": "",
    "last_band_name": "",
    "do_push": True,
    "templates": [],
    "schedule_enabled": False,
    "schedule_interval_hours": 24,
    "auto_start": False,
}


class ConfigManager:
    """설정 파일 관리"""
    
    def __init__(self, config_path: str = CONFIG_FILE):
        self.config_path = config_path
        self._data = dict(DEFAULT_CONFIG)
        self.load()
    
    def load(self) -> bool:
        """설정 파일 불러오기"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                # 기본값 위에 저장된 값 덮어쓰기
                for k, v in saved.items():
                    self._data[k] = v
                return True
            except (json.JSONDecodeError, IOError):
                pass
        return False
    
    def save(self) -> bool:
        """설정 파일 저장"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            return True
        except IOError as e:
            print(f"설정 저장 오류: {e}")
            return False
    
    def get(self, key: str, default=None):
        return self._data.get(key, default)
    
    def set(self, key: str, value):
        self._data[key] = value
    
    def update(self, data: dict):
        self._data.update(data)
        self.save()
    
    # ─── 템플릿 관리 ──────────────────────────────────────────
    def get_templates(self) -> list:
        return self._data.get("templates", [])
    
    def add_template(self, name: str, content: str) -> bool:
        templates = self.get_templates()
        # 중복 이름 체크
        for t in templates:
            if t["name"] == name:
                t["content"] = content
                self.save()
                return True
        templates.append({"name": name, "content": content})
        self._data["templates"] = templates
        self.save()
        return True
    
    def delete_template(self, name: str) -> bool:
        templates = self.get_templates()
        self._data["templates"] = [t for t in templates if t["name"] != name]
        self.save()
        return True
    
    def get_template_content(self, name: str) -> Optional[str]:
        for t in self.get_templates():
            if t["name"] == name:
                return t["content"]
        return None
