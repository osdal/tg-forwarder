"""Тест: отправляет сообщение админу от имени бота.

Запуск: uv run python -m scripts.test_bot
"""

import asyncio

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from shared.config import get_settings


async def main() -> None:
    settings = get_settings()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    me = await bot.get_me()
    print(f"✅ Бот: @{me.username} (id={me.id})")
    print(f"📤 Отправляю сообщение админу (id={settings.admin_telegram_id})...")

    try:
        msg = await bot.send_message(
            chat_id=settings.admin_telegram_id,
            text=(
                "👋 <b>Привет!</b>\n\n"
                "Это тестовое сообщение от твоего будущего бота.\n"
                "Если ты его видишь — всё работает."
            ),
        )
        print(f"✅ Отправлено! message_id={msg.message_id}")
    except Exception as e:
        print(f"❌ Ошибка: {type(e).__name__}: {e}")
        print()
        print("Возможные причины:")
        print("- Бот не нажал /start в чате с ним")
        print("- Неверный ADMIN_TELEGRAM_ID")
        print("- Бот заблокирован пользователем")

    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())