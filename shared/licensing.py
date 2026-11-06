"""Подпись лицензионных ключей (Ed25519).

Ключ = base64(payload).base64(signature), проверяется офлайн на стороне клиента.
Приватный ключ хранится только в .env сервера лицензий.
"""

import base64
import json
from datetime import datetime, timedelta

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from shared.config import DEFAULT_PLANS, get_settings

TRIAL_PLAN = "pro"
TRIAL_DAYS = 14
SIGNED_PLANS = ("free", "starter", "pro", "business")


def sign_license(client_name: str, plan: str, days: int) -> tuple[str, datetime]:
    """Возвращает (license_key, expires_at)."""
    plan = (plan or "").strip().lower()
    if plan not in SIGNED_PLANS:
        raise ValueError(f"Неверный тариф: {plan}. Доступны: {', '.join(SIGNED_PLANS)}")
    if days < 1:
        raise ValueError("Срок должен быть не меньше 1 дня.")

    settings = get_settings()
    if not settings.license_private_key:
        raise ValueError("Приватный ключ не настроен (LICENSE_PRIVATE_KEY).")

    private_key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(settings.license_private_key))
    expires = (datetime.now() + timedelta(days=days)).replace(microsecond=0)
    payload = {
        "client": client_name,
        "expires": expires.isoformat(),
        "plan": plan,
        "limits": DEFAULT_PLANS[plan],
    }
    payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode()
    signature_b64 = base64.b64encode(private_key.sign(payload_b64.encode())).decode()
    return f"{payload_b64}.{signature_b64}", expires


def format_limits(plan: str) -> str:
    limits = DEFAULT_PLANS[plan]
    sources = "без ограничений" if limits["max_sources"] == -1 else limits["max_sources"]
    targets = "без ограничений" if limits.get("max_target_channels", -1) == -1 else limits["max_target_channels"]
    ai = "да" if limits["ai_enabled"] else "нет"
    images = "да" if limits["image_gen_enabled"] else "нет"
    analytics = "да" if limits.get("analytics_enabled") else "нет"
    return f"источники: {sources}, целевые каналы: {targets}, ИИ-редактор: {ai}, картинки: {images}, аналитика: {analytics}"
