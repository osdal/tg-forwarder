"""Тест: сохраняет одно конкретное сообщение из канала в БД с медиа.

Запуск: uv run python -m scripts.test_collect_one
"""

import asyncio
import logging

from telethon import TelegramClient
from telethon.sessions import StringSession

from collector.main import (
    get_post_by_msg,
    get_source_by_telegram_id,
    save_messages_as_post,
)
from shared.config import get_settings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


CHANNEL = "@btc365_club"
MESSAGE_ID = 4091  # фото-пост


async def main() -> None:
    settings = get_settings()

    client = TelegramClient(
        StringSession(settings.collector_session),
        settings.api_id,
        settings.api_hash,
    )
    await client.start()

    entity = await client.get_entity(CHANNEL)
    msg = await client.get_messages(entity, ids=MESSAGE_ID)

    if msg is None:
        print(f"❌ Сообщение {MESSAGE_ID} не найдено в {CHANNEL}")
        await client.disconnect()
        return

    # Правильный telegram_id канала (-100...)
    full_id = int(f"-100{entity.id}")
    source = await get_source_by_telegram_id(full_id)

    if source is None:
        print(f"❌ Source {full_id} не найден в БД")
        await client.disconnect()
        return

    print(f"✅ Source: id={source.id} @{source.username}")

    existing = await get_post_by_msg(source.id, msg.id)
    if existing:
        print(f"⏭  Пост уже есть: id={existing.id}, status={existing.status}")
    else:
        post_id = await save_messages_as_post(source, [msg], msg.grouped_id)
        print(f"✅ Создан пост: id={post_id}")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())