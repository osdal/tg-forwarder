"""Проверяет все найденные .session и показывает, к каким аккаунтам они привязаны.

Запуск: uv run python -m scripts.inspect_sessions
"""

import asyncio
from pathlib import Path

from telethon import TelegramClient
from telethon.sessions import SQLiteSession

from shared.config import get_settings


SESSIONS_DIRS = [
    Path("C:/DATA/bots/telegram-forwarder"),
    Path("C:/DATA/bots/tg-monitor"),
]


async def inspect_session(session_path: Path) -> None:
    settings = get_settings()
    session_name = str(session_path.with_suffix(""))  # убираем .session

    print("-" * 60)
    print(f"Файл: {session_path.name}")
    print(f"Размер: {session_path.stat().st_size} байт")

    try:
        client = TelegramClient(
            session_name,
            settings.api_id,
            settings.api_hash,
        )
        await client.connect()

        if not await client.is_user_authorized():
            print("  ❌ Не авторизована (нужен код/вход)")
            await client.disconnect()
            return

        me = await client.get_me()
        if me is None:
            print("  ❌ Не удалось получить данные аккаунта")
            await client.disconnect()
            return

        username = f"@{me.username}" if me.username else "(без username)"
        phone = getattr(me, "phone", None) or "(скрыт)"
        print(f"  ✅ Аккаунт: id={me.id}, {me.first_name or ''} {me.last_name or ''}".strip())
        print(f"  📱 Телефон: +{phone}" if phone != "(скрыт)" else f"  📱 Телефон: скрыт")
        print(f"  🔗 Username: {username}")

        await client.disconnect()
    except Exception as e:
        print(f"  ⚠️  Ошибка: {type(e).__name__}: {e}")


async def main() -> None:
    print("=" * 60)
    print("Проверка всех .session файлов")
    print("=" * 60)
    print()

    for base_dir in SESSIONS_DIRS:
        if not base_dir.exists():
            print(f"Папка не существует: {base_dir}")
            continue

        for session_file in sorted(base_dir.glob("*.session")):
            await inspect_session(session_file)

    print()
    print("=" * 60)
    print("Готово")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())