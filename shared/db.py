from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from shared.config import get_settings


class Base(DeclarativeBase):
    pass


def resolve_database_url() -> str:
    """Выбирает URL подключения в зависимости от окружения.

    - Внутри Docker (есть файл /.dockerenv): используем DATABASE_URL (host=db).
    - Вне Docker (Windows-разработка): используем DATABASE_URL_LOCAL (host=localhost).
    """
    settings = get_settings()
    in_docker = Path("/.dockerenv").exists()

    if in_docker:
        return settings.database_url

    return settings.database_url_local or settings.database_url


engine = create_async_engine(
    resolve_database_url(),
    echo=False,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session