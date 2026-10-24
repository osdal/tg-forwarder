"""Collector — слушает каналы-источники и сохраняет посты в БД."""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from telethon import TelegramClient, events
from telethon.sessions import StringSession

from shared.config import get_settings
from shared.db import SessionLocal
from shared.models import Post, PostMedia, PostStatus, Source, AppSettings, PostTemplate
from shared.storage import save_telethon_media
from shared.telegram_utils import detect_media_type_from_telethon
from shared.publisher import publish_post_to_channel
from shared.pipeline import apply_pipeline # НОВЫЙ ИМПОРТ

# ============ Логирование ============
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("collector")
logging.getLogger("telethon").setLevel(logging.WARNING)

# ============ Буфер для альбомов ============
_album_buffer: dict[int, list] = {}
_album_tasks: dict[int, asyncio.Task] = {}
_album_chat_ids: dict[int, int] = {}
ALBUM_FLUSH_DELAY = 3.0

def build_client() -> TelegramClient:
    settings = get_settings()
    return TelegramClient(StringSession(settings.collector_session), settings.api_id, settings.api_hash)

# ============ HEARTBEAT ============
async def heartbeat() -> None:
    while True:
        try:
            naive_now = datetime.now(timezone.utc).replace(tzinfo=None)
            async with SessionLocal() as session:
                stmt = pg_insert(AppSettings).values(
                    id=1, 
                    collector_last_seen=naive_now
                ).on_conflict_do_update(
                    index_elements=[AppSettings.id],
                    set_={"collector_last_seen": naive_now}
                )
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            log.error("Heartbeat error: %s", e)
        await asyncio.sleep(10)

# ============ Работа с БД ============
async def get_active_source_ids() -> list[int]:
    async with SessionLocal() as session:
        result = await session.execute(select(Source).where(Source.enabled == True))
        return [s.telegram_id for s in result.scalars().all()]

async def get_source_by_telegram_id(telegram_id: int) -> Source | None:
    async with SessionLocal() as session:
        result = await session.execute(select(Source).where(Source.telegram_id == telegram_id))
        return result.scalar_one_or_none()

async def get_post_by_msg(source_id: int, msg_id: int) -> Post | None:
    async with SessionLocal() as session:
        result = await session.execute(select(Post).where(Post.source_id == source_id, Post.source_message_id == msg_id))
        return result.scalar_one_or_none()

async def save_messages_as_post(source: Source, messages: list, grouped_id: int | None) -> int:
    first = messages[0]
    post_uuid = f"{source.id}_{first.id}"
    stored_media = []
    
    for order, msg in enumerate(messages):
        extracted = detect_media_type_from_telethon(msg)
        if extracted is None: continue
        try:
            stored = await save_telethon_media(source_id=source.id, message=msg, extracted=extracted, post_uuid=post_uuid, order=order)
            stored_media.append(stored)
            log.info("   💾 Медиа %d сохранено: %s", order, stored.minio_key)
        except Exception as e:
            log.exception("   ❌ Ошибка сохранения медиа msg=%s: %s", msg.id, e)

    # Получаем ключ Gemini из настроек
    async with SessionLocal() as session:
        app_settings = (await session.execute(select(AppSettings).where(AppSettings.id == 1))).scalar_one_or_none()
        gemini_key = app_settings.gemini_api_key if app_settings else None

    # Применяем цепочку
    original_text = first.message or ""
    log.info("   🧠 Применяю цепочку шагов (pipeline)...")
    new_text, new_media = apply_pipeline(original_text, source.pipeline_json, api_key=gemini_key)

    async with SessionLocal() as session:
        # Сохраняем пост с уже обработанным текстом
        post = Post(
            source_id=source.id, 
            source_message_id=first.id, 
            source_grouped_id=grouped_id, 
            original_text=first.message or None, 
            edited_text=new_text if new_text != original_text else None, # Если текст не изменился, оставляем None
            pipeline_applied=True,
            status=PostStatus.NEW
        )
        session.add(post)
        await session.flush()
        
        # Добавляем оригинальные медиа
        for s in stored_media:
            session.add(PostMedia(post_id=post.id, minio_key=s.minio_key, media_type=s.media_type, order=s.order, caption=s.caption, is_user_added=False))
        
        # Добавляем медиа, сгенерированные цепочкой
        for m in new_media:
            # Ищем следующий порядковый номер
            next_order = len(stored_media) + new_media.index(m)
            session.add(PostMedia(post_id=post.id, minio_key=m["key"], media_type=m["type"], order=next_order, is_user_added=True))
        
        # АВТО-ПУБЛИКАЦИЯ
        if source.auto_publish:
            log.info("   🤖 Включена авто-публикация для источника @%s", source.username)
            if source.auto_template_id:
                log.info("   📎 Прикрепляю авто-шаблон id=%s", source.auto_template_id)
                session.add(PostTemplate(post_id=post.id, template_id=source.auto_template_id, position=0, mode="append"))
        
        await session.commit()
        await session.refresh(post)
        
        # Если авто-публикация включена, отправляем пост в канал в фоне
        if source.auto_publish:
            asyncio.create_task(publish_post_to_channel(post.id))

        return post.id

async def update_post_text(post_id: int, new_text: str | None) -> str:
    async with SessionLocal() as session:
        result = await session.execute(select(Post).where(Post.id == post_id))
        post = result.scalar_one()
        post.original_text = new_text
        if post.status != PostStatus.NEW: post.source_edited = True
        await session.commit()
        return post.status

# ============ Обработка событий ============
async def process_new_messages(chat_id: int, messages: list) -> None:
    source = await get_source_by_telegram_id(chat_id)
    if source is None:
        log.warning("⚠️  Источник telegram_id=%s не найден в БД", chat_id)
        return

    first = messages[0]
    existing = await get_post_by_msg(source.id, first.id)
    if existing is not None:
        log.info("   ⏭  Пост уже есть в БД (id=%s, status=%s)", existing.id, existing.status)
        return

    try:
        post_id = await save_messages_as_post(source, messages, first.grouped_id)
        log.info("   ✅ Создан пост id=%s (source=@%s, медиа=%d)", post_id, source.username, len(messages))
    except Exception:
        log.exception("Ошибка при сохранении поста")

async def on_new_message(event: events.NewMessage.Event) -> None:
    msg = event.message
    chat_id = event.chat_id
    if msg is None: return

    if msg.grouped_id is None:
        log.info("📩 NEW ch=%s msg=%s", chat_id, msg.id)
        await process_new_messages(chat_id, [msg])
        return

    gid = msg.grouped_id
    log.info("📩 NEW (album) ch=%s msg=%s grouped=%s", chat_id, msg.id, gid)
    _album_buffer.setdefault(gid, []).append(msg)
    _album_chat_ids[gid] = chat_id
    if gid not in _album_tasks:
        _album_tasks[gid] = asyncio.create_task(_flush_album(gid))

async def _flush_album(gid: int) -> None:
    await asyncio.sleep(ALBUM_FLUSH_DELAY)
    messages = _album_buffer.pop(gid, [])
    _album_tasks.pop(gid, None)
    chat_id = _album_chat_ids.pop(gid, None)
    if not messages or chat_id is None: return
    messages.sort(key=lambda m: m.id)
    log.info("🗂  Альбом %s: %d сообщений из ch=%s", gid, len(messages), chat_id)
    await process_new_messages(chat_id, messages)

async def on_message_edited(event: events.MessageEdited.Event) -> None:
    msg = event.message
    if msg is None: return
    log.info("✏️  EDIT ch=%s msg=%s", event.chat_id, msg.id)
    source = await get_source_by_telegram_id(event.chat_id)
    if source is None: return
    post = await get_post_by_msg(source.id, msg.id)
    if post is None: return
    new_status = await update_post_text(post.id, msg.message or None)
    log.info("   ✅ Обновлён пост id=%s (status=%s)", post.id, new_status)

# ============ Main ============
async def main() -> None:
    settings = get_settings()
    if not settings.collector_session:
        log.error("COLLECTOR_SESSION пуст.")
        return

    asyncio.create_task(heartbeat())

    client = build_client()
    log.info("Подключаюсь к Telegram...")
    await client.start()
    me = await client.get_me()
    log.info("✅ Подключено. Аккаунт: %s (id=%s)", me.first_name, me.id)

    active_sources = await get_active_source_ids()
    if not active_sources:
        log.warning("⚠️ В БД нет активных источников (или все отключены). Слушаю пустоту.")
    else:
        log.info("👀 Слушаю каналы (ID): %s", active_sources)

    client.add_event_handler(on_new_message, events.NewMessage(chats=active_sources))
    client.add_event_handler(on_message_edited, events.MessageEdited(chats=active_sources))

    log.info("Ctrl+C для остановки")
    print()
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        log.info("Остановлено пользователем")