"""AppSettings — 앱 설정을 JSON 파일에 영구 저장."""
import json
import os
import shutil

from config import DATA_DIR

SETTINGS_FILE = os.path.join(DATA_DIR, "app_settings.json")
_LEGACY_SETTINGS_FILE = r"C:\storage\med\app_settings.json"

DEFAULTS = {
    "alert_interval": 60,   # 경고 알림 간격 (초) — 기본값 1분
}


class AppSettings:
    def __init__(self, filepath=SETTINGS_FILE):
        self.filepath = filepath
        self._data    = dict(DEFAULTS)
        self._load()

    def _load(self):
        # 구 하드코딩 경로에만 파일이 있으면 DATA_DIR로 1회 이전 (알 수 없는 키 포함)
        if (
            self.filepath == SETTINGS_FILE
            and not os.path.exists(self.filepath)
            and os.path.exists(_LEGACY_SETTINGS_FILE)
        ):
            try:
                os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
                shutil.copy2(_LEGACY_SETTINGS_FILE, self.filepath)
            except Exception:
                pass
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    self._data.update(loaded)  # stretch_goal, sensitivity 등 미사용 키 보존
            except Exception:
                pass

    def _save(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self._save()

    # ── 편의 프로퍼티 ─────────────────────────────────────────────────────────
    @property
    def alert_interval(self):
        return int(self._data.get("alert_interval", DEFAULTS["alert_interval"]))

    @alert_interval.setter
    def alert_interval(self, value):
        self.set("alert_interval", int(value))


