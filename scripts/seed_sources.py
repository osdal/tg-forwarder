"""Заполняет таблицу sources и target_channels.

Запуск: uv run python -m scripts.seed_sources
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.db import SessionLocal
from shared.models import Source, TargetChannel


SOURCES = [
    {
        "telegram_id": -1001473386882,
        "title": "Know/Cryptopolia - club BTC365",
        "username": "btc365_club",
    },
    {
        "telegram_id": -1004352821786,
        "title": "AWM-Y 🇲🇽🌮",
        "username": "AWM_Y",
    },
]

TARGETS = [
    {
        "telegram_id": -1003893175003,
        "title": "Заработать в интернете просто",
        "username": "zarabotat_v_internete_prost",
    },
]


async def main() -> None:
    async with SessionLocal() as session:
        for src in SOURCES:
            stmt = pg_insert(Source).values(**src)
            stmt = stmt.on_conflict_do_update(
                index_elements=["telegram_id"],
                set_={"title": src["title"], "username": src["username"]},
            )
            await session.execute(stmt)
            print(f"✅ Source: {src['username']} (id={src['telegram_id']})")

        for tgt in TARGETS:
            stmt = pg_insert(TargetChannel).values(**tgt)
            stmt = stmt.on_conflict_do_update(
                index_elements=["telegram_id"],
                set_={"title": tgt["title"], "username": tgt["username"]},
            )
            await session.execute(stmt)
            print(f"✅ Target: {tgt['username']} (id={tgt['telegram_id']})")

        await session.commit()

    async with SessionLocal() as session:
        result = await session.execute(select(Source))
        print()
        print("📋 Sources в БД:")
        for s in result.scalars():
            print(f"   id={s.id} telegram_id={s.telegram_id} @{s.username} ({s.title})")

        result = await session.execute(select(TargetChannel))
        print()
        print("📋 TargetChannels в БД:")
        rows = list(result.scalars())
        if not rows:
            print("   (пусто)")
        for t in rows:
            print(f"   id={t.id} telegram_id={t.telegram_id} @{t.username} ({t.title})")


if __name__ == "__main__":
    asyncio.run(main())