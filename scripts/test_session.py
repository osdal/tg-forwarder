"""Проверка сохранённой COLLECTOR_SESSION.

Запуск: uv run python -m scripts.test_session
"""

import asyncio

from telethon import TelegramClient
from telethon.sessions import StringSession

from shared.config import get_settings


async def main() -> None:
    settings = get_settings()

    if not settings.collector_session:
        print("❌ COLLECTOR_SESSION пуст. Заполни в .env")
        return

    client = TelegramClient(
        StringSession(settings.collector_session),
        settings.api_id,
        settings.api_hash,
    )

    await client.connect()

    if not await client.is_user_authorized():
        print("❌ Сессия не авторизована. Сгенерируй заново.")
        await client.disconnect()
        return

    me = await client.get_me()
    print("=" * 60)
    print("✅ Сессия рабочая!")
    print("=" * 60)
    print(f"ID:       {me.id}")
    print(f"Имя:      {me.first_name} {me.last_name or ''}".strip())
    print(f"Username: @{me.username}" if me.username else "Username: (нет)")
    print(f"Телефон:  +{me.phone}" if me.phone else "Телефон: (скрыт)")
    print("=" * 60)

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())