"""Скрипт для полной очистки целевого канала от всех сообщений."""

import asyncio
import logging
from sqlalchemy import select
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import PeerChannel, Channel
from telethon.errors import ChatAdminRequiredError, MessageDeleteForbiddenError

from shared.config import get_settings
from shared.db import SessionLocal
from shared.models import TargetChannel

log = logging.getLogger("clear_channel")


async def clear_target_channel() -> tuple[bool, str]:
    settings = get_settings()
    
    async with SessionLocal() as session:
        result = await session.execute(select(TargetChannel).where(TargetChannel.enabled == True))
        target = result.scalar_one_or_none()
        if not target:
            return False, "Нет активного целевого канала в БД"
        channel_id = target.telegram_id
        channel_username = target.username
    
    client = TelegramClient(StringSession(settings.collector_session), settings.api_id, settings.api_hash)
    await client.connect()
    
    try:
        entity = None
        
        # 1. Пытаемся найти канал
        if channel_username:
            try:
                entity = await client.get_entity(channel_username)
                log.info(f"[CLEAR] Найдено по username '{channel_username}': {entity.title} (type={type(entity).__name__}, id={entity.id})")
            except Exception as e:
                log.warning(f"[CLEAR] Не удалось по username: {e}")

        if not entity:
            try:
                entity = await client.get_entity(PeerChannel(channel_id))
                log.info(f"[CLEAR] Найдено по ID {channel_id}: {entity.title}")
            except Exception as e:
                log.warning(f"[CLEAR] Не удалось по ID: {e}")

        if not entity:
            return False, "Канал не найден. Проверь, что аккаунт-сборщик — подписан на канал."

        log.info(f"[CLEAR] Начинаем удаление из канала: {entity.title}")
        
        # 2. Собираем и удаляем
        message_ids = []
        total_iterated = 0
        total_deleted = 0
        
        async for msg in client.iter_messages(entity, limit=None):
            message_ids.append(msg.id)
            total_iterated += 1
            if len(message_ids) >= 100:
                try:
                    res = await client.delete_messages(entity, message_ids, revoke=True)
                    for r in res:
                        total_deleted += r.pts_count
                except ChatAdminRequiredError:
                    return False, (
                        f"Ошибка прав: аккаунт Аллы не является администратором в канале '{entity.title}'. "
                        f"Добавь её в администраторы канала с правом 'Удалять сообщения'."
                    )
                except MessageDeleteForbiddenError:
                    return False, "Telegram запрещает удаление этих сообщений (возможно, они старше лимита или принадлежат другим пользователям)."
                
                log.info(f"[CLEAR] Пачка: обработано={total_iterated}, реально удалено={total_deleted}")
                message_ids = []
                await asyncio.sleep(1)
        
        # Финальная пачка
        if message_ids:
            try:
                res = await client.delete_messages(entity, message_ids, revoke=True)
                for r in res:
                    total_deleted += r.pts_count
            except ChatAdminRequiredError:
                return False, (
                    f"Ошибка прав: аккаунт Аллы не является администратором в канале '{entity.title}'. "
                    f"Добавь её в администраторы канала с правом 'Удалять сообщения'."
                )
            except MessageDeleteForbiddenError:
                return False, "Telegram запрещает удаление этих сообщений."
            
            log.info(f"[CLEAR] Финальная пачка: обработано={total_iterated}, реально удалено={total_deleted}")

        # 3. Проверяем остатки
        await asyncio.sleep(2)
        remaining = 0
        async for _ in client.iter_messages(entity, limit=10):
            remaining += 1
        
        log.info(f"[CLEAR] После удаления в канале осталось (первые 10): {remaining}")

        if total_deleted == 0 and total_iterated > 0:
            return False, (
                f"Канал '{entity.title}' найден, но Telegram отказал в удалении. "
                f"Скорее всего, у Аллы нет прав администратора. Добавь её в админы канала."
            )

        if remaining > 0:
            return False, (
                f"Частично: удалено {total_deleted} из {total_iterated}. "
                f"В канале ещё есть сообщения (смотри лог бэкенда)."
            )
            
        return True, f"Канал '{entity.title}' очищен. Удалено сообщений: {total_deleted}"
        
    except Exception as e:
        log.exception("[CLEAR] Ошибка при очистке канала")
        return False, str(e)
    finally:
        await client.disconnect()