"""Telegram-бот админа."""

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload

from shared.config import get_settings
from shared.db import SessionLocal
from shared.models import Post, PostStatus, TargetChannel, Source, AppSettings
from shared.storage import load_media_bytes, mark_media_published
from shared.publisher import publish_post_to_channel
from shared.ai_helper import translate_text, rewrite_text
from shared.minio_client import get_minio

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("bot")
logging.getLogger("aiogram").setLevel(logging.WARNING)

settings = get_settings()
bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

class AdminStates(StatesGroup):
    waiting_for_edit_text = State()
    waiting_for_schedule_time = State()

def build_post_keyboard(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"approve:{post_id}"),
             InlineKeyboardButton(text="🗑 В корзину", callback_data=f"delete:{post_id}")],
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit:{post_id}"),
             InlineKeyboardButton(text="🕒 Отложить", callback_data=f"schedule:{post_id}")],
        ]
    )

def build_caption(post: Post, media_count: int) -> str:
    text = post.original_text or ""
    preview = text[:300] + ("..." if len(text) > 300 else "")
    source = post.source.username if post.source else "?"
    edited_mark = " (изменён)" if post.edited_text else ""
    return f"📩 <b>Новый пост</b> из @{source}\n🆔 post_id={post.id}{edited_mark}\n🖼 Медиа: {media_count}\n\n{preview}"

# --- HEARTBEAT ---
async def heartbeat() -> None:
    while True:
        try:
            async with SessionLocal() as session:
                stmt = pg_insert(AppSettings).values(
                    id=1, 
                    admin_telegram_id=settings.admin_telegram_id,
                    bot_last_seen=datetime.now(timezone.utc)
                ).on_conflict_do_update(
                    index_elements=[AppSettings.id],
                    set_={"bot_last_seen": datetime.now(timezone.utc)}
                )
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            log.error("Heartbeat error: %s", e)
        await asyncio.sleep(10)

# --- ФОНОВЫЕ ЗАДАЧИ ---
async def poll_new_posts() -> None:
    while True:
        try:
            async with SessionLocal() as session:
                result = await session.execute(select(Post).where(Post.status == PostStatus.NEW, Post.notified == False).options(selectinload(Post.source), selectinload(Post.media)).order_by(Post.id).limit(5))
                for post in list(result.scalars()):
                    try:
                        caption = build_caption(post, len(post.media))
                        if not post.media:
                            await bot.send_message(chat_id=settings.admin_telegram_id, text=caption + "\n\n(без медиа)", reply_markup=build_post_keyboard(post.id))
                        else:
                            first = post.media[0]; data = load_media_bytes(first.minio_key)
                            ext = first.minio_key.rsplit(".", 1)[-1].lower()
                            file = BufferedInputFile(data, filename=f"media.{ext}")
                            if ext in ("jpg", "jpeg", "png", "webp"):
                                await bot.send_photo(chat_id=settings.admin_telegram_id, photo=file, caption=caption, reply_markup=build_post_keyboard(post.id))
                            else:
                                await bot.send_document(chat_id=settings.admin_telegram_id, document=file, caption=caption, reply_markup=build_post_keyboard(post.id))
                        post.notified = True
                        await session.commit()
                    except Exception as e: log.exception("Ошибка уведомления id=%s", post.id)
        except Exception: pass
        await asyncio.sleep(10)

async def poll_scheduled_posts() -> None:
    while True:
        try:
            now = datetime.now(timezone.utc)
            async with SessionLocal() as session:
                result = await session.execute(select(Post).where(Post.status == PostStatus.SCHEDULED, Post.publish_at <= now).limit(5))
                for post in list(result.scalars()):
                    success, err = await publish_post_to_channel(post.id)
                    if success:
                        await bot.send_message(chat_id=settings.admin_telegram_id, text=f"⏰ Отложенный пост <b>id={post.id}</b> опубликован.")
                    else:
                        post.status = PostStatus.NEW
                        await session.commit()
        except Exception: pass
        await asyncio.sleep(60)

async def poll_cleanup_trash() -> None:
    while True:
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=3)
            async with SessionLocal() as session:
                result = await session.execute(select(Post).where(Post.status == PostStatus.DELETED, Post.deleted_at <= cutoff).options(selectinload(Post.media)))
                posts = list(result.scalars())
                if posts:
                    log.info("🧹 Очистка корзины: удаляю %s старых постов", len(posts))
                    for post in posts:
                        for m in post.media:
                            get_minio().delete(m.minio_key)
                        await session.delete(post)
                    await session.commit()
        except Exception: log.exception("Ошибка очистки корзины")
        await asyncio.sleep(3600)

# --- ОБРАБОТЧИКИ ---
@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    if message.from_user.id != settings.admin_telegram_id: return
    await message.answer("👋 Привет! Я бот для управления публикациями.")

@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Действие отменено.")

@dp.message(F.forward_from_chat)
async def handle_forwarded_channel(message: Message) -> None:
    if message.from_user.id != settings.admin_telegram_id: return
    chat = message.forward_from_chat
    if chat.type not in ('channel', 'supergroup'): return
    async with SessionLocal() as session:
        if (await session.execute(select(Source).where(Source.telegram_id == chat.id))).scalar_one_or_none(): return
        session.add(Source(telegram_id=chat.id, title=chat.title, username=chat.username or f"private_{abs(chat.id)}", enabled=True))
        await session.commit()
    await message.answer(f"✅ Канал <b>{chat.title}</b> добавлен!")

@dp.callback_query(F.data.startswith("approve:"))
async def cb_approve(callback: CallbackQuery) -> None:
    post_id = int(callback.data.split(":")[1])
    await callback.answer("⏳ Публикую...")
    success, err = await publish_post_to_channel(post_id)
    if success:
        try:
            if callback.message.caption: await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n✅ <b>Опубликовано</b>", reply_markup=None)
            else: await callback.message.edit_text(text=f"{callback.message.text}\n\n✅ <b>Опубликовано</b>", reply_markup=None)
        except Exception: pass
    else: await callback.message.reply(f"❌ Ошибка: {err}", parse_mode=None)

@dp.callback_query(F.data.startswith("delete:"))
async def cb_delete(callback: CallbackQuery) -> None:
    post_id = int(callback.data.split(":")[1])
    async with SessionLocal() as session:
        post = (await session.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
        if post:
            post.status = PostStatus.DELETED
            post.deleted_at = datetime.now(timezone.utc)
            await session.commit()
            await callback.answer(f"🗑 Перемещено в корзину")
            try:
                if callback.message.caption: await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n🗑 <b>В корзине</b>", reply_markup=None)
                else: await callback.message.edit_text(text=f"{callback.message.text}\n\n🗑 <b>В корзине</b>", reply_markup=None)
            except Exception: pass

def get_edit_ai_keyboard(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Перевести", callback_data=f"ai_trans:{post_id}"),
         InlineKeyboardButton(text="🔄 Рерайт", callback_data=f"ai_rewr:{post_id}")]
    ])

@dp.callback_query(F.data.startswith("edit:"))
async def cb_edit(callback: CallbackQuery, state: FSMContext) -> None:
    post_id = int(callback.data.split(":")[1])
    await state.set_state(AdminStates.waiting_for_edit_text)
    await state.update_data(post_id=post_id)
    await callback.message.reply(f"✏️ Отправь новый текст для поста <b>id={post_id}</b>.\nЛибо используй ИИ:", reply_markup=get_edit_ai_keyboard(post_id))
    await callback.answer()

@dp.callback_query(F.data.startswith("ai_trans:"))
async def cb_ai_translate(callback: CallbackQuery, state: FSMContext) -> None:
    post_id = int(callback.data.split(":")[1])
    await callback.answer("Перевожу...")
    async with SessionLocal() as session:
        post = (await session.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
        if not post: return
        text = post.edited_text or post.original_text or ""
    await bot.send_chat_action(chat_id=callback.from_user.id, action="typing")
    try:
        translated = translate_text(text)
        async with SessionLocal() as session:
            post = (await session.execute(select(Post).where(Post.id == post_id))).scalar_one()
            post.edited_text = translated
            await session.commit()
        await callback.message.reply(f"✅ <b>Переведено:</b>\n\n{translated}", reply_markup=get_edit_ai_keyboard(post_id))
    except Exception as e: await callback.message.reply(f"❌ Ошибка ИИ: {e}")

@dp.callback_query(F.data.startswith("ai_rewr:"))
async def cb_ai_rewrite(callback: CallbackQuery, state: FSMContext) -> None:
    post_id = int(callback.data.split(":")[1])
    await callback.answer("Делаю рерайт...")
    async with SessionLocal() as session:
        post = (await session.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
        if not post: return
        text = post.edited_text or post.original_text or ""
    await bot.send_chat_action(chat_id=callback.from_user.id, action="typing")
    try:
        rewritten = rewrite_text(text)
        async with SessionLocal() as session:
            post = (await session.execute(select(Post).where(Post.id == post_id))).scalar_one()
            post.edited_text = rewritten
            await session.commit()
        await callback.message.reply(f"✅ <b>Рерайт готов:</b>\n\n{rewritten}", reply_markup=get_edit_ai_keyboard(post_id))
    except Exception as e: await callback.message.reply(f"❌ Ошибка ИИ: {e}")

@dp.message(AdminStates.waiting_for_edit_text)
async def process_edit_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data(); post_id = data.get("post_id")
    async with SessionLocal() as session:
        post = (await session.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
        if post:
            post.edited_text = message.text or message.caption or ""
            await session.commit()
            await message.answer(f"✅ Текст поста <b>id={post_id}</b> обновлён.", reply_markup=build_post_keyboard(post.id))
    await state.clear()

@dp.callback_query(F.data.startswith("schedule:"))
async def cb_schedule(callback: CallbackQuery, state: FSMContext) -> None:
    post_id = int(callback.data.split(":")[1])
    await state.set_state(AdminStates.waiting_for_schedule_time)
    await state.update_data(post_id=post_id)
    await callback.message.reply(f"🕒 Введи время в формате <code>ЧЧ:ММ</code> или <code>ГГГГ-ММ-ДД ЧЧ:ММ</code>:")
    await callback.answer()

@dp.message(AdminStates.waiting_for_schedule_time)
async def process_schedule_time(message: Message, state: FSMContext) -> None:
    data = await state.get_data(); post_id = data.get("post_id"); text = message.text.strip()
    try:
        now = datetime.now()
        if ":" in text and "-" not in text:
            t = datetime.strptime(text, "%H:%M").time(); target_dt = datetime.combine(now.date(), t)
            if target_dt < now: target_dt += timedelta(days=1)
        else: target_dt = datetime.strptime(text, "%Y-%m-%d %H:%M")
        async with SessionLocal() as session:
            post = (await session.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
            if post:
                post.status = PostStatus.SCHEDULED; post.publish_at = target_dt.astimezone(timezone.utc)
                await session.commit()
                await message.answer(f"🕒 Пост отложен на {target_dt.strftime('%Y-%m-%d %H:%M')}.", reply_markup=None)
    except ValueError: return await message.answer("❌ Неверный формат.")
    await state.clear()

async def main() -> None:
    me = await bot.get_me()
    log.info("✅ Бот: @%s", me.username)
    asyncio.create_task(heartbeat())
    asyncio.create_task(poll_new_posts())
    asyncio.create_task(poll_scheduled_posts())
    asyncio.create_task(poll_cleanup_trash())
    await dp.start_polling(bot)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass