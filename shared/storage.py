"""Логика сохранения и извлечения медиа."""

import uuid
from dataclasses import dataclass

from shared.minio_client import get_minio
from shared.models import MediaType
from shared.telegram_utils import (
    ExtractedMedia,
    build_minio_key,
    guess_extension,
)


@dataclass
class StoredMedia:
    """Результат сохранения одного файла в MinIO."""

    minio_key: str
    media_type: MediaType
    order: int
    caption: str | None
    file_name: str | None
    mime_type: str | None


async def download_from_telethon(message, extracted: ExtractedMedia) -> bytes:
    """Скачивает байты медиа из Telethon-сообщения."""
    from telethon.tl.types import MessageMediaPhoto

    if isinstance(message.media, MessageMediaPhoto):
        return await message.download_media(file=bytes)

    data = await message.download_media(file=bytes)
    if data is None:
        raise RuntimeError(
            f"Telethon не смог скачать медиа из сообщения {message.id}"
        )
    return data


async def save_telethon_media(
    *,
    source_id: int,
    message,
    extracted: ExtractedMedia,
    post_uuid: str,
    order: int,
) -> StoredMedia:
    """Скачивает медиа из Telethon и загружает в MinIO."""
    data = await download_from_telethon(message, extracted)

    extension = guess_extension(extracted.mime_type, extracted.media_type)
    key = build_minio_key(source_id, post_uuid, order, extension)

    minio = get_minio()
    minio.upload_bytes(
        key=key,
        data=data,
        content_type=extracted.mime_type or "application/octet-stream",
        tags={"temporary": "true"},
    )

    return StoredMedia(
        minio_key=key,
        media_type=extracted.media_type,
        order=order,
        caption=extracted.caption,
        file_name=extracted.file_name,
        mime_type=extracted.mime_type,
    )


def new_post_uuid() -> str:
    """Уникальный идентификатор поста для группировки медиа в MinIO."""
    return uuid.uuid4().hex


def load_media_bytes(minio_key: str) -> bytes:
    """Возвращает содержимое объекта из MinIO."""
    return get_minio().download_bytes(minio_key)


def mark_media_published(minio_key: str) -> None:
    """Ставит тег published=true (lifecycle удалит через 1 день)."""
    get_minio().set_tags(minio_key, {"published": "true"})


def mark_media_keep(minio_key: str) -> None:
    """Помечает объект как постоянный — не удаляется lifecycle."""
    get_minio().set_tags(minio_key, {"keep": "true"})


def delete_media(keys: list[str]) -> None:
    """Удаляет объекты из MinIO (идемпотентно)."""
    get_minio().delete_many(keys)