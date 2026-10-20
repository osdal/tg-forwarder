"""Одноразовый скрипт генерации StringSession через QR-код (PNG-картинка)
с автоматическим обновлением токена.

Запуск: uv run python -m scripts.generate_session
"""

import asyncio
from pathlib import Path

import qrcode

from telethon import TelegramClient
from telethon.sessions import StringSession

from shared.config import get_settings


def save_qr(url: str, path: Path) -> None:
    """Сохраняет QR-код в PNG, обходя проблемы PIL на Windows."""
    # Удаляем старый файл, если он есть
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass

    img = qrcode.make(url)

    # Явно открываем файл и передаём его в save — обходит проблему
    # с путями и локами на Windows
    with open(path, "wb") as f:
        img.save(f, format="PNG")


async def main() -> None:
    settings = get_settings()

    print("=" * 60)
    print("Генерация StringSession (вход по QR-коду через PNG)")
    print("=" * 60)
    print()

    client = TelegramClient(
        StringSession(),
        settings.api_id,
        settings.api_hash,
    )

    await client.connect()

    if not await client.is_user_authorized():
        qr_login = await client.qr_login()

        qr_path = Path.cwd() / "qr_login.png"
        last_url = None

        while True:
            if qr_login.url != last_url:
                last_url = qr_login.url
                save_qr(qr_login.url, qr_path)

                print("=" * 60)
                print("QR-КОД ОБНОВЛЁН. Открой картинку:")
                print(f"  {qr_path}")
                print("=" * 60)
                print()
                print("ЧТО ДЕЛАТЬ:")
                print("1. Открой qr_login.png в проводнике Windows")
                print("2. На телефоне с аккаунтом-сборщиком:")
                print("   Telegram -> Настройки -> Устройства -> Подключить устройство")
                print("3. Наведи камеру телефона на QR-код на экране монитора")
                print()
                print("Если QR истёк — картинка обновится автоматически.")
                print("Ctrl+C для отмены.")
                print()

            try:
                await qr_login.wait(timeout=10)
                print("✅ Успешный вход!")
                break
            except asyncio.TimeoutError:
                print("⏳ QR-код истёк, создаю новый...")
                await qr_login.recreate()

    session_string = client.session.save()

    print()
    print("=" * 60)
    print("Готово! Скопируй строку ниже и вставь в .env в COLLECTOR_SESSION")
    print("=" * 60)
    print()
    print(session_string)
    print()
    print("=" * 60)

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())