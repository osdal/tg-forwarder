"""Получает ID канала по username.

Запуск: uv run python -m scripts.get_channel_id
"""

import asyncio

from telethon import TelegramClient
from telethon.sessions import StringSession

from shared.config import get_settings


CHANNELS = [
    "@zarabotat_v_internete_prost",
]


async def main() -> None:
    settings = get_settings()

    client = TelegramClient(
        StringSession(settings.collector_session),
        settings.api_id,
        settings.api_hash,
    )

    await client.start()

    for username in CHANNELS:
        try:
            entity = await client.get_entity(username)
            # Для каналов/супергрупп ID имеет формат -100XXXXXXXXXX
            # Telethon возвращает "сырой" ID, добавляем префикс -100
            raw_id = entity.id
            full_id = int(f"-100{raw_id}")

            print(f"✅ {username}:")
            print(f"   raw_id      = {raw_id}")
            print(f"   telegram_id = {full_id}")
            print(f"   title       = {entity.title}")
            print()
        except Exception as e:
            print(f"❌ {username}: {type(e).__name__}: {e}")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())