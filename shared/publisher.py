"""Общая логика публикации постов в целевой канал."""

import logging
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BufferedInputFile, InputMediaPhoto, InputMediaVideo, InputMediaDocument, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from shared.config import get_settings
from shared.db import SessionLocal
from shared.models import (
    Post, PostStatus, TargetChannel, PostTemplate, 
    SourceTemplate, Template, Source
)
from shared.storage import load_media_bytes, mark_media_published

log = logging.getLogger("publisher")

settings = get_settings()
bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

def split_text_into_chunks(text: str, limit: int) -> list[str]:
    """Разбивает текст на части, не превышающие лимит."""
    if not text:
        return []
    parts = []
    while len(text) > limit:
        split_idx = text.rfind('\n', 0, limit)
        if split_idx == -1:
            split_idx = text.rfind(' ', 0, limit)
        if split_idx == -1:
            split_idx = limit
        
        parts.append(text[:split_idx].strip())
        text = text[split_idx:].strip()
    
    if text:
        parts.append(text)
    return parts

async def get_first_target_channel() -> TargetChannel | None:
    async with SessionLocal() as session:
        result = await session.execute(select(TargetChannel).where(TargetChannel.enabled == True).limit(1))
        return result.scalar_one_or_none()

def build_inline_keyboard(buttons_json: list | None) -> InlineKeyboardMarkup | None:
    if not buttons_json:
        return None
    keyboard = []
    for btn in buttons_json:
        if isinstance(btn, dict) and "text" in btn and "url" in btn:
            keyboard.append([InlineKeyboardButton(text=btn["text"], url=btn["url"])])
    return InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None

async def send_separate_template(chat_id: int, template: Template):
    text = template.text or ""
    media_json = template.media_json or []
    reply_markup = build_inline_keyboard(template.buttons_json)
    
    if not media_json:
        if text or reply_markup:
            text_parts = split_text_into_chunks(text, 4096)
            for i, part in enumerate(text_parts):
                rm = reply_markup if i == len(text_parts) - 1 else None
                await bot.send_message(chat_id=chat_id, text=part, reply_markup=rm)
        return

    media_list = []
    caption_text = text
    remaining_text = ""
    
    if len(caption_text) > 1024:
        split_idx = caption_text.rfind('\n', 0, 1024)
        if split_idx == -1:
            split_idx = caption_text.rfind(' ', 0, 1024)
        if split_idx == -1:
            split_idx = 1024
        caption_text = caption_text[:split_idx].strip()
        remaining_text = text[split_idx:].strip()

    for i, item in enumerate(media_json):
        data = load_media_bytes(item["key"])
        ext = item["key"].rsplit(".", 1)[-1].lower()
        file = BufferedInputFile(data, filename=f"media.{ext}")
        
        # Передаем caption сразу при создании, а не после
        caption = caption_text if i == 0 else None

        if item["type"] in ("photo", "animation"):
            media_list.append(InputMediaPhoto(media=file, caption=caption))
        elif item["type"] in ("video", "voice", "audio"):
            media_list.append(InputMediaVideo(media=file, caption=caption))
        else:
            media_list.append(InputMediaDocument(media=file, caption=caption))

    sent_messages = []
    if len(media_list) == 1:
        # Для одиночного медиа caption уже внутри объекта, но send_photo ждет его отдельно
        # Поэтому мы используем прямую отправку файла
        if isinstance(media_list[0], InputMediaPhoto):
            sent = await bot.send_photo(chat_id=chat_id, photo=media_list[0].media, caption=caption_text, reply_markup=reply_markup)
        else:
            sent = await bot.send_document(chat_id=chat_id, document=media_list[0].media, caption=caption_text, reply_markup=reply_markup)
        sent_messages.append(sent)
    else:
        sent = await bot.send_media_group(chat_id=chat_id, media=media_list)
        if isinstance(sent, list):
            sent_messages.extend(sent)
        else:
            sent_messages.append(sent)
            
        if reply_markup:
            kb_msg = await bot.send_message(chat_id=chat_id, text="👇", reply_markup=reply_markup, reply_to_message_id=sent_messages[0].message_id)
            sent_messages.append(kb_msg)

    if remaining_text:
        text_parts = split_text_into_chunks(remaining_text, 4096)
        for part in text_parts:
            reply_to_id = sent_messages[0].message_id if sent_messages else None
            sent_msg = await bot.send_message(chat_id=chat_id, text=part, reply_to_message_id=reply_to_id)
            sent_messages.append(sent_msg)

async def publish_post_to_channel(post_id: int) -> tuple[bool, str]:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Post)
            .where(Post.id == post_id)
            .options(
                selectinload(Post.media),
                selectinload(Post.templates).selectinload(PostTemplate.template),
                selectinload(Post.source).selectinload(Source.templates).selectinload(SourceTemplate.template)
            )
        )
        post = result.scalar_one_or_none()

        if not post or post.status not in (PostStatus.NEW, PostStatus.APPROVED, PostStatus.SCHEDULED):
            return False, "Пост не найден или уже опубликован/удалён."

        target = await get_first_target_channel()
        if not target:
            return False, "В БД нет активного целевого канала."

        all_buttons = []
        if post.buttons_json:
            all_buttons.extend(post.buttons_json)

        base_text = post.edited_text or post.original_text or ""
        prepend_texts = []
        append_texts = []
        all_media_items = []
        
        for m in post.media:
            all_media_items.append({"key": m.minio_key, "type": m.media_type})

        if hasattr(post, 'templates') and post.templates:
            for pt in post.templates:
                t = pt.template
                if not t: continue
                
                current_mode = pt.mode or t.attach_mode 
                
                if t.text:
                    if current_mode == "prepend": prepend_texts.append(t.text)
                    elif current_mode == "append": append_texts.append(t.text)
                if t.media_json:
                    for tm in t.media_json:
                        all_media_items.append({"key": tm["key"], "type": tm["type"]})
                if t.buttons_json:
                    all_buttons.extend(t.buttons_json)

        reply_markup = build_inline_keyboard(all_buttons)

        parts = []
        if prepend_texts: parts.append("\n\n".join(prepend_texts))
        if base_text: parts.append(base_text)
        if append_texts: parts.append("\n\n".join(append_texts))
        final_text = "\n\n".join(parts)

        caption_text = final_text
        remaining_text = ""
        
        if len(caption_text) > 1024:
            split_idx = caption_text.rfind('\n', 0, 1024)
            if split_idx == -1:
                split_idx = caption_text.rfind(' ', 0, 1024)
            if split_idx == -1:
                split_idx = 1024
            caption_text = caption_text[:split_idx].strip()
            remaining_text = final_text[split_idx:].strip()

        media_list = []
        for i, item in enumerate(all_media_items):
            data = load_media_bytes(item["key"])
            ext = item["key"].rsplit(".", 1)[-1].lower()
            file = BufferedInputFile(data, filename=f"media.{ext}")

            # Передаем caption только для первого элемента
            caption = caption_text if i == 0 else None

            if item["type"] in ("photo", "animation"):
                media_list.append(InputMediaPhoto(media=file, caption=caption))
            elif item["type"] in ("video", "voice", "audio"):
                media_list.append(InputMediaVideo(media=file, caption=caption))
            else:
                media_list.append(InputMediaDocument(media=file, caption=caption))

        try:
            sent_messages = []

            if not media_list:
                text_parts = split_text_into_chunks(final_text, 4096)
                if not text_parts:
                    return False, "Пост пуст (нет ни текста, ни медиа)."
                
                for i, part in enumerate(text_parts):
                    rm = reply_markup if i == len(text_parts) - 1 else None
                    sent = await bot.send_message(chat_id=target.telegram_id, text=part, reply_markup=rm)
                    sent_messages.append(sent)
            else:
                if len(media_list) == 1:
                    if isinstance(media_list[0], InputMediaPhoto):
                        sent = await bot.send_photo(chat_id=target.telegram_id, photo=media_list[0].media, caption=caption_text, reply_markup=reply_markup)
                    else:
                        sent = await bot.send_document(chat_id=target.telegram_id, document=media_list[0].media, caption=caption_text, reply_markup=reply_markup)
                    sent_messages.append(sent)
                else:
                    sent = await bot.send_media_group(chat_id=target.telegram_id, media=media_list)
                    if isinstance(sent, list):
                        sent_messages.extend(sent)
                    else:
                        sent_messages.append(sent)
                        
                    if reply_markup:
                        kb_msg = await bot.send_message(chat_id=target.telegram_id, text="👇", reply_markup=reply_markup, reply_to_message_id=sent_messages[0].message_id)
                        sent_messages.append(kb_msg)
                
                if remaining_text:
                    text_parts = split_text_into_chunks(remaining_text, 4096)
                    for part in text_parts:
                        reply_to_id = sent_messages[0].message_id if sent_messages else None
                        sent_msg = await bot.send_message(chat_id=target.telegram_id, text=part, reply_to_message_id=reply_to_id)
                        sent_messages.append(sent_msg)

            post.status = PostStatus.PUBLISHED
            post.published_at = datetime.now(timezone.utc)
            post.target_channel_id = target.id
            post.published_message_id = sent_messages[0].message_id if sent_messages else None

            await session.commit()

            for m in post.media:
                mark_media_published(m.minio_key)

            if post.source and post.source.templates:
                for st in post.source.templates:
                    if st.template:
                        try:
                            await send_separate_template(target.telegram_id, st.template)
                        except Exception as e:
                            log.error("Не удалось отправить шаблон источника %s: %s", st.template.id, e)

            return True, ""
        except Exception as e:
            log.exception("Ошибка публикации поста id=%s", post_id)
            return False, str(e)