"""配置管理 — 设备码、登录态等持久化存储"""

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".coolapk-mcp"
CONFIG_FILE = CONFIG_DIR / "config.json"


class AppConfig:
    """应用配置，持久化到 ~/.coolapk-mcp/config.json"""

    def __init__(self):
        self.device_code: str = ""
        self.uid: str = ""
        self.username: str = ""
        self.token: str = ""  # 登录后的 cookie token
        self.api_base: str = "https://api.coolapk.com"

    @property
    def is_logged_in(self) -> bool:
        return bool(self.uid and self.token)

    def get_cookies(self) -> dict[str, str]:
        if not self.is_logged_in:
            return {}
        return {"uid": self.uid, "username": self.username, "token": self.token}

    @classmethod
    def load(cls) -> "AppConfig":
        """从配置文件加载，不存在则初始化"""
        config = cls()
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
                config.device_code = data.get("device_code", "")
                config.uid = data.get("uid", "")
                config.username = data.get("username", "")
                config.token = data.get("token", "")
                config.api_base = data.get("api_base", "https://api.coolapk.com")
            except (json.JSONDecodeError, KeyError):
                pass

        if not config.device_code:
            from coolapk_mcp.auth.device import generate_device_code

            config.device_code = generate_device_code()
            config.save()

        return config

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(
                {
                    "device_code": self.device_code,
                    "uid": self.uid,
                    "username": self.username,
                    "token": self.token,
                    "api_base": self.api_base,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
