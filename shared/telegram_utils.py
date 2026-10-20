"""Хелперы для работы с Telegram-медиа.

Преобразует объекты Telethon / aiogram в простые структуры,
пригодные для сохранения в БД и MinIO.
"""

from dataclasses import dataclass
from typing import Any

from shared.models import MediaType


@dataclass
class ExtractedMedia:
    """Медиа, извлечённое из сообщения Telegram."""

    media_type: MediaType
    file_id: str | None       # Для aiogram (publisher)
    file_unique_id: str | None
    file_name: str | None
    mime_type: str | None
    file_size: int | None
    width: int | None = None
    height: int | None = None
    duration: int | None = None
    caption: str | None = None


def detect_media_type_from_telethon(message: Any) -> ExtractedMedia | None:
    """Определяет тип медиа из сообщения Telethon."""
    from telethon.tl.types import (
        DocumentAttributeAudio,
        DocumentAttributeVideo,
        MessageMediaDocument,
        MessageMediaPhoto,
    )

    if message.photo:
        return ExtractedMedia(
            media_type=MediaType.PHOTO,
            file_id=None,
            file_unique_id=None,
            file_name=None,
            mime_type="image/jpeg",
            file_size=None,
            width=getattr(message.photo, "w", None),
            height=getattr(message.photo, "h", None),
            caption=message.message or None,
        )

    media = message.media
    if isinstance(media, MessageMediaDocument) and media.document:
        doc = media.document
        mime = doc.mime_type or ""

        media_type = MediaType.DOCUMENT
        duration = None
        width = None
        height = None

        if mime.startswith("video/"):
            media_type = MediaType.VIDEO
        elif mime.startswith("audio/"):
            media_type = MediaType.AUDIO
        elif mime.startswith("image/"):
            media_type = MediaType.ANIMATION

        for attr in doc.attributes:
            if isinstance(attr, DocumentAttributeVideo):
                media_type = MediaType.VIDEO
                duration = attr.duration
                width = attr.w
                height = attr.h
            elif isinstance(attr, DocumentAttributeAudio):
                if attr.voice:
                    media_type = MediaType.VOICE
                else:
                    media_type = MediaType.AUDIO
                duration = attr.duration

        file_name = None
        for attr in doc.attributes:
            if hasattr(attr, "file_name"):
                file_name = attr.file_name
                break

        return ExtractedMedia(
            media_type=media_type,
            file_id=None,
            file_unique_id=None,
            file_name=file_name,
            mime_type=mime,
            file_size=doc.size,
            width=width,
            height=height,
            duration=duration,
            caption=message.message or None,
        )

    return None


def guess_extension(mime_type: str | None, media_type: MediaType) -> str:
    """Подбирает расширение файла по MIME-типу или типу медиа."""
    if mime_type:
        mapping = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
            "video/mp4": ".mp4",
            "video/quicktime": ".mov",
            "video/x-matroska": ".mkv",
            "audio/mpeg": ".mp3",
            "audio/ogg": ".ogg",
            "audio/mp4": ".m4a",
            "application/pdf": ".pdf",
        }
        if mime_type in mapping:
            return mapping[mime_type]

    fallback = {
        MediaType.PHOTO: ".jpg",
        MediaType.VIDEO: ".mp4",
        MediaType.AUDIO: ".mp3",
        MediaType.VOICE: ".ogg",
        MediaType.ANIMATION: ".gif",
        MediaType.DOCUMENT: ".bin",
    }
    return fallback.get(media_type, ".bin")


def build_minio_key(
    source_id: int,
    post_uuid: str,
    order: int,
    extension: str,
) -> str:
    """Формирует ключ объекта в MinIO для медиа из источника."""
    return f"sources/{source_id}/{post_uuid}/{order:02d}{extension}"


def build_user_media_key(post_uuid: str, order: int, extension: str) -> str:
    """Ключ для медиа, добавленного вручную через веб-панель."""
    return f"user/{post_uuid}/{order:02d}{extension}"


def build_template_media_key(
    template_id: int, order: int, extension: str
) -> str:
    """Ключ для медиа шаблона."""
    return f"templates/{template_id}/{order:02d}{extension}"