from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db import Base

# ============ ENUM'ы ============
class PostStatus(StrEnum):
    NEW = "new"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    DELETED = "deleted"

class MediaType(StrEnum):
    PHOTO = "photo"
    VIDEO = "video"
    DOCUMENT = "document"
    AUDIO = "audio"
    VOICE = "voice"
    ANIMATION = "animation"

class TemplateAttachMode(StrEnum):
    STANDALONE = "standalone"
    APPEND = "append"
    PREPEND = "prepend"

# ============ ИСТОЧНИКИ ============
class Source(Base):
    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # НОВЫЕ ПОЛЯ
    auto_publish: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    auto_template_id: Mapped[int | None] = mapped_column(ForeignKey("templates.id", ondelete="SET NULL"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    posts: Mapped[list["Post"]] = relationship(back_populates="source")
    templates: Mapped[list["SourceTemplate"]] = relationship(back_populates="source", cascade="all, delete-orphan")
    auto_template: Mapped["Template | None"] = relationship(foreign_keys=[auto_template_id])

# ============ ЦЕЛЕВЫЕ КАНАЛЫ ============
class TargetChannel(Base):
    __tablename__ = "target_channels"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    posts: Mapped[list["Post"]] = relationship(back_populates="target_channel")

# ============ ПОСТЫ ============
class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        UniqueConstraint("source_id", "source_message_id", name="uq_post_source_msg"),
        Index("ix_posts_status_created", "status", "created_at"),
        Index("ix_posts_status_publish_at", "status", "publish_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    source_message_id: Mapped[int] = mapped_column(BigInteger)
    source_grouped_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)

    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    edited_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    buttons_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    target_channel_id: Mapped[int | None] = mapped_column(ForeignKey("target_channels.id", ondelete="SET NULL"), nullable=True)

    status: Mapped[str] = mapped_column(String(20), default=PostStatus.NEW, index=True)
    source_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    notified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", index=True)

    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    source: Mapped["Source"] = relationship(back_populates="posts")
    target_channel: Mapped["TargetChannel | None"] = relationship(back_populates="posts")
    media: Mapped[list["PostMedia"]] = relationship(back_populates="post", cascade="all, delete-orphan", order_by="PostMedia.order")
    templates: Mapped[list["PostTemplate"]] = relationship(back_populates="post", cascade="all, delete-orphan", order_by="PostTemplate.position")

# ============ МЕДИА ПОСТА ============
class PostMedia(Base):
    __tablename__ = "post_media"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    minio_key: Mapped[str] = mapped_column(String(500))
    media_type: Mapped[str] = mapped_column(String(20))
    order: Mapped[int] = mapped_column(Integer, default=0)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_user_added: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    post: Mapped["Post"] = relationship(back_populates="media")

# ============ МЕДИА-БИБЛИОТЕКА ============
class MediaLibrary(Base):
    __tablename__ = "media_library"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    minio_key: Mapped[str] = mapped_column(String(500), unique=True)
    media_type: Mapped[str] = mapped_column(String(20))
    original_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

# ============ ПАПКИ ШАБЛОНОВ ============
class TemplateFolder(Base):
    __tablename__ = "template_folders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    templates: Mapped[list["Template"]] = relationship(back_populates="folder")

# ============ ШАБЛОНЫ ============
class Template(Base):
    __tablename__ = "templates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    folder_id: Mapped[int | None] = mapped_column(ForeignKey("template_folders.id", ondelete="SET NULL"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    buttons_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    attach_mode: Mapped[str] = mapped_column(String(20), default=TemplateAttachMode.STANDALONE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    folder: Mapped["TemplateFolder | None"] = relationship(back_populates="templates")
    posts: Mapped[list["PostTemplate"]] = relationship(back_populates="template", cascade="all, delete-orphan")
    sources: Mapped[list["SourceTemplate"]] = relationship(back_populates="template", cascade="all, delete-orphan")

class PostTemplate(Base):
    __tablename__ = "post_templates"
    __table_args__ = (UniqueConstraint("post_id", "template_id", name="uq_post_template"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    post: Mapped["Post"] = relationship(back_populates="templates")
    template: Mapped["Template"] = relationship(back_populates="posts")

class SourceTemplate(Base):
    __tablename__ = "source_templates"
    __table_args__ = (UniqueConstraint("source_id", "template_id", name="uq_source_template"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id", ondelete="CASCADE"), index=True)
    source: Mapped["Source"] = relationship(back_populates="templates")
    template: Mapped["Template"] = relationship(back_populates="sources")

# ============ МЕТРИКИ ============
class MetricDaily(Base):
    __tablename__ = "metrics_daily"
    __table_args__ = (UniqueConstraint("date", "source_id", "target_channel_id", name="uq_metric_day"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    target_channel_id: Mapped[int | None] = mapped_column(ForeignKey("target_channels.id", ondelete="SET NULL"), nullable=True)
    collected: Mapped[int] = mapped_column(Integer, default=0)
    published: Mapped[int] = mapped_column(Integer, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    pending: Mapped[int] = mapped_column(Integer, default=0)

# ============ НАСТРОЙКИ ============
class AppSettings(Base):
    __tablename__ = "app_settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    admin_telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    admin_telegram_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bot_last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    collector_last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())