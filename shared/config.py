import base64
import json
import sys
from datetime import datetime
from pydantic_settings import BaseSettings
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

PUBLIC_KEY_B64 = "DbDMH8BpoqPV+N/abLYanCaHOsIX2KaECp/M/V2oJ6o="

DEFAULT_PLANS = {
    "free":     {"max_sources": 5,  "ai_enabled": False, "image_gen_enabled": False},
    "pro":      {"max_sources": 50, "ai_enabled": True,  "image_gen_enabled": True},
    "business": {"max_sources": -1, "ai_enabled": True,  "image_gen_enabled": True},
    "owner":    {"max_sources": -1, "ai_enabled": True,  "image_gen_enabled": True},
}

class LicenseInfo:
    def __init__(self, client: str, expires: datetime, plan: str, limits: dict):
        self.client = client
        self.expires = expires
        self.plan = plan
        self.limits = limits

    def is_valid(self) -> bool:
        return datetime.now() < self.expires

    def get(self, key: str, default=None):
        return self.limits.get(key, default)

    def to_dict(self):
        return {
            "client": self.client,
            "expires": self.expires.isoformat(),
            "plan": self.plan,
            "limits": self.limits,
        }

def parse_license(license_key: str) -> LicenseInfo | None:
    if not license_key:
        return None
    try:
        # Очищаем от кавычек и пробелов
        license_key = license_key.strip().strip('"').strip("'")
        payload_b64, signature_b64 = license_key.split(".")
        
        payload_b64 = payload_b64.strip()
        signature_b64 = signature_b64.strip()
        
        # Функция для восстановления паддинга base64
        def fix_padding(s: str) -> str:
            return s + "=" * (-len(s) % 4)

        payload_b64 = fix_padding(payload_b64)
        signature_b64 = fix_padding(signature_b64)
        pub_key_b64 = fix_padding(PUBLIC_KEY_B64.strip())

        public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(pub_key_b64))
        public_key.verify(base64.b64decode(signature_b64), payload_b64.encode())
        
        payload = json.loads(base64.b64decode(payload_b64))
        expires = datetime.fromisoformat(payload["expires"])
        plan = payload.get("plan", "free")
        limits = payload.get("limits") or DEFAULT_PLANS.get(plan, DEFAULT_PLANS["free"])
        return LicenseInfo(client=payload.get("client", "Unknown"), expires=expires, plan=plan, limits=limits)
    except (InvalidSignature, ValueError) as e:
        print(f"❌ Неверная подпись лицензии: {e}")
        return None
    except Exception as e:
        print(f"❌ Ошибка парсинга лицензии: {e}")
        return None

class Settings(BaseSettings):
    api_id: int
    api_hash: str
    collector_session: str | None = None
    bot_token: str
    admin_telegram_id: int
    bot_username: str = "tel_forw_bot"

    postgres_user: str = "tgforwarder"
    postgres_password: str = "change_me"
    postgres_db: str = "tgforwarder"
    database_url: str
    database_url_local: str | None = None

    redis_url: str = "redis://redis:6379/0"

    minio_root_user: str = "minioadmin"
    minio_root_password: str = "change_me"
    minio_endpoint: str = "minio:9000"
    minio_endpoint_local: str | None = None
    minio_bucket: str = "media"
    minio_public_url: str = "http://localhost:9000"

    jwt_secret: str = "change_me_to_long_random_string"
    web_public_url: str = "http://localhost:8000"

    gemini_api_key: str | None = None

    license_key: str = ""
    license_private_key: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def get_license(self) -> LicenseInfo:
        lic = parse_license(self.license_key)
        if not lic:
            raise ValueError("❌ ЛИЦЕНЗИЯ НЕДЕЙСТВИТЕЛЬНА ИЛИ ПРОСРОЧЕНА!")
        if not lic.is_valid():
            raise ValueError(f"❌ ЛИЦЕНЗИЯ ИСТЕКЛА {lic.expires}.")
        return lic

def get_settings():
    return Settings()

settings = get_settings()

# Проверяем лицензию при старте, НО пропускаем проверку для миграций Alembic
if any("alembic" in arg for arg in sys.argv):
    license_info = LicenseInfo("Migration", datetime(2099, 1, 1), "owner", DEFAULT_PLANS["owner"])
else:
    license_info = settings.get_license()
    print(f"✅ Лицензия: план={license_info.plan}, клиент={license_info.client}, действует до {license_info.expires}")