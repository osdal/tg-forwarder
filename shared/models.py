from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()

class PostStatus(str, enum.Enum):
    NEW = "new"
    APPROVED = "approved"
    PUBLISHED = "published"
    SCHEDULED = "scheduled"
    DELETED = "deleted"

class MediaType(str, enum.Enum):
    PHOTO = "photo"
    VIDEO = "video"
    DOCUMENT = "document"
    AUDIO = "audio"
    VOICE = "voice"
    ANIMATION = "animation"

class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, index=True)
    title = Column(String)
    username = Column(String, unique=True, index=True)
    enabled = Column(Boolean, default=True)
    auto_publish = Column(Boolean, default=False)
    auto_template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)
    pipeline_json = Column(Text, nullable=True) # НОВОЕ ПОЛЕ
    templates = relationship("SourceTemplate", back_populates="source", cascade="all, delete-orphan")

class TargetChannel(Base):
    __tablename__ = "target_channels"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, index=True)
    title = Column(String)
    username = Column(String, nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("sources.id"))
    source_message_id = Column(BigInteger)
    source_grouped_id = Column(BigInteger, nullable=True, index=True)
    original_text = Column(Text, nullable=True)
    edited_text = Column(Text, nullable=True)
    status = Column(String, default=PostStatus.NEW.value)
    source_edited = Column(Boolean, default=False, nullable=False)
    publish_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    target_channel_id = Column(Integer, ForeignKey("target_channels.id"), nullable=True)
    published_message_id = Column(BigInteger, nullable=True)
    notified = Column(Boolean, default=False)
    buttons_json = Column(JSONB, nullable=True)
    pipeline_applied = Column(Boolean, default=False) # НОВОЕ ПОЛЕ
    
    source = relationship("Source")
    media = relationship("PostMedia", back_populates="post", cascade="all, delete-orphan")
    templates = relationship("PostTemplate", back_populates="post", cascade="all, delete-orphan")

class PostMedia(Base):
    __tablename__ = "post_media"
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"))
    minio_key = Column(String)
    media_type = Column(String)
    order = Column(Integer, default=0)
    caption = Column(Text, nullable=True)
    is_user_added = Column(Boolean, default=False)
    post = relationship("Post", back_populates="media")

class TemplateFolder(Base):
    __tablename__ = "template_folders"
    id = Column(Integer, primary_key=True)
    name = Column(String)

class Template(Base):
    __tablename__ = "templates"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    text = Column(Text)
    attach_mode = Column(String, default="append")
    folder_id = Column(Integer, ForeignKey("template_folders.id"), nullable=True)
    media_json = Column(JSONB, nullable=True)
    buttons_json = Column(JSONB, nullable=True)

class PostTemplate(Base):
    __tablename__ = "post_templates"
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"))
    template_id = Column(Integer, ForeignKey("templates.id"))
    position = Column(Integer, default=0)
    mode = Column(String, nullable=True)
    post = relationship("Post", back_populates="templates")
    template = relationship("Template")

class SourceTemplate(Base):
    __tablename__ = "source_templates"
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("sources.id"))
    template_id = Column(Integer, ForeignKey("templates.id"))
    source = relationship("Source", back_populates="templates")
    template = relationship("Template")

class MediaLibrary(Base):
    __tablename__ = "media_library"
    id = Column(Integer, primary_key=True)
    minio_key = Column(String)
    media_type = Column(String)
    original_name = Column(String, nullable=True)

class AppSettings(Base):
    __tablename__ = "app_settings"
    id = Column(Integer, primary_key=True)
    bot_last_seen = Column(DateTime, nullable=True)
    collector_last_seen = Column(DateTime, nullable=True)
    gemini_api_key = Column(String, nullable=True) # НОВОЕ ПОЛЕ

class MetricsDaily(Base):
    __tablename__ = "metrics_daily"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    target_channel_id = Column(Integer, ForeignKey("target_channels.id"), nullable=True)
    collected = Column(Integer, default=0)
    published = Column(Integer, default=0)
    deleted = Column(Integer, default=0)
    pending = Column(Integer, default=0)

class ClientLicense(Base):
    __tablename__ = "client_licenses"
    id = Column(Integer, primary_key=True)
    client_name = Column(String, index=True)
    license_key = Column(Text)
    plan = Column(String)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)