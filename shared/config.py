import base64
import json
import logging
from datetime import datetime
from pydantic_settings import BaseSettings
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

# Временная заглушка. Скрипт scripts/setup_license.py заменит её на твой ключ.
PUBLIC_KEY_B64 = "9MEr27MLBbwBIQ/vJl/3heO65Ry/+olzxujCJaI5A98="

def validate_license(license_key: str) -> bool:
    if PUBLIC_KEY_B64 == "9MEr27MLBbwBIQ/vJl/3heO65Ry/+olzxujCJaI5A98=":
        # Если ключ не заменен (режим разработки), пропускаем проверку
        return True
    
    if not license_key:
        return False
    try:
        payload_b64, signature_b64 = license_key.split(".")
        public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(PUBLIC_KEY_B64))
        public_key.verify(base64.b64decode(signature_b64), payload_b64.encode())
        
        payload = json.loads(base64.b64decode(payload_b64))
        expires = datetime.fromisoformat(payload["expires"])
        if datetime.now() > expires:
            print(f"❌ Лицензия истекла {expires}")
            return False
        return True
    except (InvalidSignature, ValueError) as e:
        print(f"❌ Неверная подпись лицензии: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка валидации лицензии: {e}")
        return False

class Settings(BaseSettings):
    # Telegram
    api_id: int
    api_hash: str
    collector_session: str | None = None
    bot_token: str
    admin_telegram_id: int
    bot_username: str = "tel_forw_bot"

    # Database
    postgres_user: str = "tgforwarder"
    postgres_password: str = "change_me"
    postgres_db: str = "tgforwarder"
    database_url: str
    database_url_local: str | None = None

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # MinIO
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "change_me"
    minio_endpoint: str = "minio:9000"
    minio_endpoint_local: str | None = None
    minio_bucket: str = "media"
    minio_public_url: str = "http://localhost:9000"

    # Web
    jwt_secret: str = "change_me_to_long_random_string"
    web_public_url: str = "http://localhost:8000"

    # AI
    gemini_api_key: str | None = None

    # License
    license_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

# Функция-обертка, которую ждут другие модули
def get_settings():
    return Settings()

settings = get_settings()

# Проверяем лицензию при старте любого контейнера
if not validate_license(settings.license_key):
    raise ValueError("❌ ЛИЦЕНЗИЯ НЕДЕЙСТВИТЕЛЬНА ИЛИ ПРОСРОЧЕНА! Обратитесь к разработчику.")