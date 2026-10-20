"""Принудительное скачивание медиа для поста."""
import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from telethon import TelegramClient
from telethon.sessions import StringSession

from shared.config import get_settings
from shared.db import SessionLocal
from shared.models import Post, PostMedia, Source
from shared.storage import save_telethon_media
from shared.telegram_utils import detect_media_type_from_telethon

log = logging.getLogger("refetch")

async def refetch_post_media(post_id: int) -> tuple[bool, str]:
    settings = get_settings()
    
    async with SessionLocal() as session:
        result = await session.execute(
            select(Post).where(Post.id == post_id).options(selectinload(Post.source), selectinload(Post.media))
        )
        post = result.scalar_one_or_none()
        if not post:
            return False, "Пост не найден в БД"
        
        if not post.source:
            return False, "У поста нет источника"
            
        if not post.media:
            return False, "У этого поста нет медиа (только текст)"

        source_id = post.source.id
        chat_id = post.source.telegram_id
        msg_id = post.source_message_id
        
        # Удаляем старые битые записи о медиа
        for m in post.media:
            await session.delete(m)
        await session.commit()

    client = TelegramClient(StringSession(settings.collector_session), settings.api_id, settings.api_hash)
    await client.connect()
    
    try:
        entity = await client.get_entity(chat_id)
        msg = await client.get_messages(entity, ids=msg_id)
        
        if not msg or not msg.media:
            return False, "В Telegram у этого сообщения больше нет медиа"
            
        extracted = detect_media_type_from_telethon(msg)
        if not extracted:
            return False, "Не удалось определить тип медиа"
            
        post_uuid = f"{source_id}_{msg.id}"
        
        # Скачиваем
        stored = await save_telethon_media(
            source_id=source_id,
            message=msg,
            extracted=extracted,
            post_uuid=post_uuid,
            order=0
        )
        
        # Сохраняем в БД
        async with SessionLocal() as session:
            session.add(PostMedia(
                post_id=post_id, 
                minio_key=stored.minio_key, 
                media_type=stored.media_type, 
                order=0, 
                is_user_added=False
            ))
            await session.commit()
            
        return True, "Медиа успешно скачано!"
        
    except Exception as e:
        log.exception("Ошибка при скачивании")
        return False, str(e)
    finally:
        await client.disconnect()