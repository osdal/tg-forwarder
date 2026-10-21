"""FastAPI backend для веб-панели."""

import io
import os
import time
import uuid
import subprocess
import sys
import hmac
import hashlib
import jwt
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, File, UploadFile, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import select, func, case
from sqlalchemy.orm import selectinload
from telethon import TelegramClient
from telethon.sessions import StringSession

from shared.config import get_settings
from shared.db import SessionLocal
from shared.models import Post, PostStatus, PostMedia, Template, PostTemplate, TemplateFolder, Source, SourceTemplate, MediaLibrary, AppSettings
from shared.publisher import publish_post_to_channel
from shared.minio_client import get_minio
from shared.ai_helper import translate_text, rewrite_text, generate_text
from shared.text_utils import remove_links
from shared.process_manager import start_process, stop_process, is_running, kill_all_python_by_module
from scripts.refetch_media import refetch_post_media
from scripts.clear_target_channel import clear_target_channel

settings = get_settings()
app = FastAPI(title="TG Forwarder Web API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)

def create_access_token(data: dict):
    to_encode = data.copy(); expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire}); return jwt.encode(to_encode, settings.jwt_secret, algorithm="HS256")

def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials: raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=["HS256"])
        if payload.get("sub") != str(settings.admin_telegram_id): raise HTTPException(status_code=403, detail="Forbidden")
        return payload
    except jwt.PyJWTError: raise HTTPException(status_code=401, detail="Invalid token")

# --- УПРАВЛЕНИЕ ПРОЦЕССАМИ ---
class ProcessAction(BaseModel):
    name: str

@app.get("/api/processes/status")
async def get_processes_status(_=Depends(get_current_admin)):
    return {"bot": is_running("bot"), "collector": is_running("collector")}

@app.post("/api/processes/start")
async def start_service(data: ProcessAction, _=Depends(get_current_admin)):
    if data.name == "bot": success, msg = start_process("bot", "bot.main")
    elif data.name == "collector": success, msg = start_process("collector", "collector.main")
    else: raise HTTPException(status_code=400, detail="Неизвестный процесс")
    if success: return {"status": "ok", "message": msg}
    raise HTTPException(status_code=400, detail=msg)

@app.post("/api/processes/stop")
async def stop_service(data: ProcessAction, _=Depends(get_current_admin)):
    success, msg = stop_process(data.name)
    if success: return {"status": "ok", "message": msg}
    raise HTTPException(status_code=400, detail=msg)

@app.post("/api/processes/force-kill-all")
async def force_kill_all(_=Depends(get_current_admin)):
    bot_count = kill_all_python_by_module("bot.main")
    collector_count = kill_all_python_by_module("collector.main")
    return {"status": "ok", "message": f"Убито {bot_count} bot-процессов и {collector_count} collector-процессов"}

# --- СТАТУС HEARTBEAT ---
@app.get("/api/status")
async def get_status(_=Depends(get_current_admin)):
    async with SessionLocal() as session:
        s = (await session.execute(select(AppSettings).where(AppSettings.id == 1))).scalar_one_or_none()
        now = datetime.now(timezone.utc)
        bot_online = False; collector_online = False
        if s:
            if s.bot_last_seen and (now - s.bot_last_seen).total_seconds() < 30: bot_online = True
            if s.collector_last_seen and (now - s.collector_last_seen).total_seconds() < 30: collector_online = True
        return {"bot_online": bot_online, "collector_online": collector_online}

# --- ИИ ---
class AITextRequest(BaseModel):
    text: str
    word_count: int | None = None

class AIGenerateRequest(BaseModel):
    prompt: str
    base_text: str | None = None

@app.post("/api/ai/translate")
async def api_translate(data: AITextRequest, _=Depends(get_current_admin)):
    try: return {"result": translate_text(data.text)}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/rewrite")
async def api_rewrite(data: AITextRequest, _=Depends(get_current_admin)):
    try: return {"result": rewrite_text(data.text, data.word_count)}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/remove-links")
async def api_remove_links(data: AITextRequest, _=Depends(get_current_admin)):
    try: return {"result": remove_links(data.text)}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/generate")
async def api_generate(data: AIGenerateRequest, _=Depends(get_current_admin)):
    try: 
        result = generate_text(data.prompt, data.base_text or "")
        return {"result": result}
    except Exception as e: 
        raise HTTPException(status_code=500, detail=str(e))

# --- АВТОРИЗАЦИЯ ---
class TelegramAuthData(BaseModel):
    id: int; first_name: str | None = None; last_name: str | None = None; username: str | None = None; photo_url: str | None = None; auth_date: int; hash: str
class DevLoginData(BaseModel):
    password: str

@app.post("/api/auth/telegram")
async def telegram_auth(data: TelegramAuthData):
    data_dict = data.model_dump(exclude={"hash"}); data_dict = {k: str(v) for k, v in data_dict.items() if v is not None}
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data_dict.items()))
    secret_key = hashlib.sha256(settings.bot_token.encode()).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if computed_hash != data.hash: raise HTTPException(status_code=401, detail="Invalid hash")
    if data.id != settings.admin_telegram_id: raise HTTPException(status_code=403, detail="Access denied")
    return {"token": create_access_token({"sub": str(data.id)})}

@app.post("/api/auth/dev")
async def dev_auth(data: DevLoginData):
    if data.password == settings.jwt_secret: return {"token": create_access_token({"sub": str(settings.admin_telegram_id)})}
    raise HTTPException(status_code=401, detail="Wrong password")

# --- ИСТОЧНИКИ ---
@app.get("/api/sources")
async def get_sources(_=Depends(get_current_admin)):
    async with SessionLocal() as session:
        result = await session.execute(select(Source).options(selectinload(Source.templates).selectinload(SourceTemplate.template)).order_by(Source.id))
        return [{
            "id": s.id, "telegram_id": s.telegram_id, "title": s.title, "username": s.username, "enabled": s.enabled, 
            "auto_publish": s.auto_publish, "auto_template_id": s.auto_template_id,
            "templates": [{"id": st.template.id, "name": st.template.name} for st in s.templates]
        } for s in result.scalars().all()]

class SourceCreate(BaseModel):
    channel_input: str

@app.post("/api/sources")
async def add_source(data: SourceCreate, _=Depends(get_current_admin)):
    clean_input = data.channel_input.strip()
    is_numeric_id = False
    if clean_input.startswith('-100') and clean_input[1:].isdigit(): is_numeric_id = True; telegram_id = int(clean_input)
    elif clean_input.isdigit(): is_numeric_id = True; telegram_id = int(clean_input)

    if is_numeric_id:
        async with SessionLocal() as session:
            if (await session.execute(select(Source).where(Source.telegram_id == telegram_id))).scalar_one_or_none(): raise HTTPException(status_code=400, detail="ID уже добавлен")
            new_source = Source(telegram_id=telegram_id, title=f"Приватный {telegram_id}", username=f"private_{abs(telegram_id)}", enabled=True)
            session.add(new_source); await session.commit(); return {"status": "ok", "id": new_source.id}
    else:
        async with SessionLocal() as session:
            if (await session.execute(select(Source).where(Source.username == clean_input.replace('@', '')))).scalar_one_or_none(): raise HTTPException(status_code=400, detail="Уже добавлен")
        client = TelegramClient(StringSession(settings.collector_session), settings.api_id, settings.api_hash); await client.connect()
        try:
            entity = await client.get_entity(clean_input); from telethon.utils import get_peer_id
            telegram_id = get_peer_id(entity); title = entity.title; username = getattr(entity, 'username', None) or str(telegram_id)
            async with SessionLocal() as session:
                new_source = Source(telegram_id=telegram_id, title=title, username=username, enabled=True)
                session.add(new_source); await session.commit(); return {"status": "ok", "id": new_source.id}
        except Exception as e: raise HTTPException(status_code=400, detail=f"Ошибка: {str(e)}")
        finally: await client.disconnect()

@app.patch("/api/sources/{source_id}/toggle")
async def toggle_source(source_id: int, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        source = (await session.execute(select(Source).where(Source.id == source_id))).scalar_one_or_none()
        if not source: raise HTTPException(status_code=404)
        source.enabled = not source.enabled; await session.commit(); return {"status": "ok", "enabled": source.enabled}

class AutoPublishUpdate(BaseModel):
    auto_publish: bool
    auto_template_id: int | None = None

@app.patch("/api/sources/{source_id}/auto-publish")
async def update_auto_publish(source_id: int, data: AutoPublishUpdate, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        source = (await session.execute(select(Source).where(Source.id == source_id))).scalar_one_or_none()
        if not source: raise HTTPException(status_code=404)
        source.auto_publish = data.auto_publish
        source.auto_template_id = data.auto_template_id
        await session.commit(); return {"status": "ok"}

@app.delete("/api/sources/{source_id}")
async def delete_source(source_id: int, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        source = (await session.execute(select(Source).where(Source.id == source_id))).scalar_one_or_none()
        if not source: raise HTTPException(status_code=404)
        await session.delete(source); await session.commit(); return {"status": "ok"}

class AttachSourceTemplate(BaseModel):
    template_id: int

@app.post("/api/sources/{source_id}/templates")
async def attach_source_template(source_id: int, data: AttachSourceTemplate, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        if (await session.execute(select(SourceTemplate).where(SourceTemplate.source_id == source_id, SourceTemplate.template_id == data.template_id))).scalar_one_or_none(): return {"status": "ok"}
        session.add(SourceTemplate(source_id=source_id, template_id=data.template_id)); await session.commit(); return {"status": "ok"}

@app.delete("/api/sources/{source_id}/templates/{template_id}")
async def detach_source_template(source_id: int, template_id: int, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        st = (await session.execute(select(SourceTemplate).where(SourceTemplate.source_id == source_id, SourceTemplate.template_id == template_id))).scalar_one_or_none()
        if st: await session.delete(st); await session.commit()
        return {"status": "ok"}

# --- ЗАГРУЗКА (ОБЩАЯ) ---
@app.post("/api/upload")
async def upload_generic_media(file: UploadFile = File(...), _=Depends(get_current_admin)):
    data = await file.read(); ext = file.filename.split('.')[-1].lower() if file.filename and '.' in file.filename else "jpg"
    if ext not in ("jpg", "jpeg", "png", "webp", "gif", "mp4"): ext = "jpg"
    key = f"templates/{uuid.uuid4().hex[:8]}.{ext}"
    get_minio().upload_bytes(key, data, content_type=file.content_type or "image/jpeg", tags={"keep": "true"})
    return {"key": key, "type": "video" if ext == "mp4" else "photo"}

# --- МЕДИА-БИБЛИОТЕКА ---
@app.get("/api/media-library")
async def get_media_library(_=Depends(get_current_admin)):
    async with SessionLocal() as session:
        result = await session.execute(select(MediaLibrary).order_by(MediaLibrary.id.desc()))
        return [{"id": m.id, "key": m.minio_key, "type": m.media_type, "name": m.original_name} for m in result.scalars().all()]

@app.post("/api/media-library/upload")
async def upload_to_library(file: UploadFile = File(...), _=Depends(get_current_admin)):
    data = await file.read(); ext = file.filename.split('.')[-1].lower() if file.filename and '.' in file.filename else "jpg"
    if ext not in ("jpg", "jpeg", "png", "webp", "gif", "mp4"): ext = "jpg"
    key = f"library/{uuid.uuid4().hex[:8]}.{ext}"
    get_minio().upload_bytes(key, data, content_type=file.content_type or "image/jpeg", tags={"keep": "true"})
    async with SessionLocal() as session:
        m = MediaLibrary(minio_key=key, media_type="video" if ext=="mp4" else "photo", original_name=file.filename)
        session.add(m); await session.commit(); return {"status": "ok", "id": m.id}

@app.post("/api/posts/{post_id}/media/save-to-library/{media_id}")
async def save_to_library(post_id: int, media_id: int, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        pm = (await session.execute(select(PostMedia).where(PostMedia.id == media_id, PostMedia.post_id == post_id))).scalar_one_or_none()
        if not pm: raise HTTPException(status_code=404, detail="Медиа поста не найдено")
        try:
            data = get_minio().download_bytes(pm.minio_key)
        except Exception:
            raise HTTPException(status_code=404, detail="Файл физически отсутствует в хранилище")
        ext = pm.minio_key.rsplit(".", 1)[-1].lower() if "." in pm.minio_key else "jpg"
        new_key = f"library/{uuid.uuid4().hex[:8]}.{ext}"
        get_minio().upload_bytes(new_key, data, tags={"keep": "true"})
        m = MediaLibrary(minio_key=new_key, media_type=pm.media_type, original_name="saved_from_post")
        session.add(m); await session.commit(); return {"status": "ok"}

@app.post("/api/posts/{post_id}/media/from-library/{lib_id}")
async def attach_from_library(post_id: int, lib_id: int, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        post = (await session.execute(select(Post).where(Post.id == post_id).options(selectinload(Post.media)))).scalar_one_or_none()
        if not post: raise HTTPException(status_code=404)
        lib = (await session.execute(select(MediaLibrary).where(MediaLibrary.id == lib_id))).scalar_one_or_none()
        if not lib: raise HTTPException(status_code=404)
        session.add(PostMedia(post_id=post.id, minio_key=lib.minio_key, media_type=lib.media_type, order=len(post.media), is_user_added=True))
        await session.commit(); return {"status": "ok"}

@app.delete("/api/media-library/{lib_id}")
async def delete_from_library(lib_id: int, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        lib = (await session.execute(select(MediaLibrary).where(MediaLibrary.id == lib_id))).scalar_one_or_none()
        if not lib: raise HTTPException(status_code=404)
        get_minio().delete(lib.minio_key); await session.delete(lib); await session.commit(); return {"status": "ok"}

# --- ПОСТЫ ---
@app.get("/")
def read_root(): return {"status": "ok"}

@app.get("/api/posts")
async def get_posts(trash: bool = False, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        query = select(Post).options(selectinload(Post.source), selectinload(Post.media), selectinload(Post.templates).selectinload(PostTemplate.template))
        if trash: query = query.where(Post.status == PostStatus.DELETED).order_by(Post.deleted_at.desc())
        else: query = query.where(Post.status != PostStatus.DELETED).order_by(Post.id.desc())
        result = await session.execute(query.limit(100))
        return [{"id": p.id, "source": p.source.username if p.source else None, "text": p.edited_text or p.original_text, "status": p.status, "created_at": p.created_at.isoformat() if p.created_at else None, "media_count": len(p.media), "media": [{"id": m.id, "type": m.media_type, "key": m.minio_key} for m in p.media], "templates": [{"id": pt.template.id, "name": pt.template.name, "mode": pt.mode or pt.template.attach_mode} for pt in p.templates], "buttons_json": p.buttons_json} for p in result.scalars().all()]

@app.post("/api/manual-post")
async def create_manual_post(_=Depends(get_current_admin)):
    async with SessionLocal() as session:
        try:
            source = (await session.execute(select(Source).where(Source.username == "manual"))).scalar_one_or_none()
            if not source:
                source = Source(telegram_id=-999999999, title="Ручной пост", username="manual", enabled=False)
                session.add(source)
                await session.commit()
                await session.refresh(source)

            msg_id = -int(time.time() * 1000) - int(uuid.uuid4().int % 1000)

            post = Post(
                source_id=source.id,
                source_message_id=msg_id,
                original_text="",
                status=PostStatus.NEW,
                notified=True
            )
            session.add(post)
            await session.commit()
            await session.refresh(post)
            return {"status": "ok", "id": post.id}
            
        except Exception as e:
            await session.rollback()
            print(f"ERROR CREATING MANUAL POST: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/posts/{post_id}")
async def get_single_post(post_id: int, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        result = await session.execute(
            select(Post).where(Post.id == post_id).options(
                selectinload(Post.source), selectinload(Post.media),
                selectinload(Post.templates).selectinload(PostTemplate.template)
            )
        )
        p = result.scalar_one_or_none()
        if not p: raise HTTPException(status_code=404)
        return {
            "id": p.id, "source": p.source.username if p.source else None,
            "text": p.edited_text or p.original_text, "status": p.status,
            "media_count": len(p.media),
            "media": [{"id": m.id, "type": m.media_type, "key": m.minio_key} for m in p.media],
            "templates": [{"id": pt.template.id, "name": pt.template.name, "mode": pt.mode or pt.template.attach_mode} for pt in p.templates],
            "buttons_json": p.buttons_json
        }

@app.post("/api/posts/{post_id}/approve")
async def approve_post(post_id: int, _=Depends(get_current_admin)):
    success, err = await publish_post_to_channel(post_id)
    if success: return {"status": "ok"}
    raise HTTPException(status_code=400, detail=err)

@app.post("/api/posts/{post_id}/refetch")
async def refetch_media(post_id: int, _=Depends(get_current_admin)):
    success, msg = await refetch_post_media(post_id)
    if success: return {"status": "ok", "message": msg}
    raise HTTPException(status_code=400, detail=msg)

@app.post("/api/posts/{post_id}/unpublish")
async def unpublish_post(post_id: int, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        post = (await session.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
        if not post: raise HTTPException(status_code=404)
        if post.status != PostStatus.PUBLISHED: raise HTTPException(status_code=400, detail="Пост не был опубликован")
        post.status = PostStatus.NEW; post.published_at = None
        await session.commit(); return {"status": "ok"}

@app.post("/api/posts/{post_id}/delete")
async def delete_post(post_id: int, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        post = (await session.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
        if not post: raise HTTPException(status_code=404)
        post.status = PostStatus.DELETED; post.deleted_at = datetime.now(timezone.utc)
        await session.commit(); return {"status": "ok"}

@app.post("/api/posts/{post_id}/restore")
async def restore_post(post_id: int, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        post = (await session.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
        if not post: raise HTTPException(status_code=404)
        post.status = PostStatus.NEW; post.deleted_at = None
        await session.commit(); return {"status": "ok"}

@app.delete("/api/posts/{post_id}/purge")
async def purge_post(post_id: int, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        post = (await session.execute(select(Post).where(Post.id == post_id).options(selectinload(Post.media)))).scalar_one_or_none()
        if not post: raise HTTPException(status_code=404)
        for m in post.media:
            if (await session.execute(select(MediaLibrary).where(MediaLibrary.minio_key == m.minio_key))).scalar_one_or_none(): pass
            else: get_minio().delete(m.minio_key)
        await session.delete(post); await session.commit(); return {"status": "ok"}

@app.delete("/api/posts/trash/empty")
async def empty_trash(_=Depends(get_current_admin)):
    async with SessionLocal() as session:
        result = await session.execute(select(Post).where(Post.status == PostStatus.DELETED).options(selectinload(Post.media)))
        for post in result.scalars().all():
            for m in post.media:
                if not (await session.execute(select(MediaLibrary).where(MediaLibrary.minio_key == m.minio_key))).scalar_one_or_none(): get_minio().delete(m.minio_key)
            await session.delete(post)
        await session.commit(); return {"status": "ok"}

class PostUpdate(BaseModel):
    text: str
    buttons_json: list | None = None

@app.patch("/api/posts/{post_id}")
async def update_post_text(post_id: int, data: PostUpdate, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        post = (await session.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
        if not post: raise HTTPException(status_code=404)
        post.edited_text = data.text if data.text != post.original_text else None
        post.buttons_json = data.buttons_json
        await session.commit(); return {"status": "ok"}

@app.post("/api/posts/{post_id}/media")
async def upload_media(post_id: int, file: UploadFile = File(...), _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        post = (await session.execute(select(Post).where(Post.id == post_id).options(selectinload(Post.media)))).scalar_one_or_none()
        if not post: raise HTTPException(status_code=404)
        data = await file.read(); ext = file.filename.split('.')[-1].lower() if file.filename and '.' in file.filename else "jpg"
        if ext not in ("jpg", "jpeg", "png", "webp", "gif", "mp4"): ext = "jpg"
        minio_key = f"user/{post_id}_{uuid.uuid4().hex[:6]}.{ext}"
        get_minio().upload_bytes(minio_key, data, content_type=file.content_type or "image/jpeg", tags={"keep": "true"})
        session.add(PostMedia(post_id=post.id, minio_key=minio_key, media_type="video" if ext == "mp4" else "photo", order=len(post.media), is_user_added=True))
        await session.commit(); return {"status": "ok"}

@app.delete("/api/media/{media_id}")
async def delete_media(media_id: int, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        media = (await session.execute(select(PostMedia).where(PostMedia.id == media_id))).scalar_one_or_none()
        if not media: raise HTTPException(status_code=404)
        get_minio().delete(media.minio_key); await session.delete(media); await session.commit(); return {"status": "ok"}

# --- ПАПКИ ШАБЛОНОВ ---
class FolderCreate(BaseModel):
    name: str

@app.get("/api/template-folders")
async def get_folders(_=Depends(get_current_admin)):
    async with SessionLocal() as session:
        return [{"id": f.id, "name": f.name} for f in (await session.execute(select(TemplateFolder).order_by(TemplateFolder.name))).scalars().all()]

@app.post("/api/template-folders")
async def create_folder(data: FolderCreate, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        f = TemplateFolder(name=data.name); session.add(f); await session.commit(); return {"status": "ok", "id": f.id}

@app.delete("/api/template-folders/{folder_id}")
async def delete_folder(folder_id: int, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        f = (await session.execute(select(TemplateFolder).where(TemplateFolder.id == folder_id))).scalar_one_or_none()
        if not f: raise HTTPException(status_code=404)
        await session.delete(f); await session.commit(); return {"status": "ok"}

# --- ШАБЛОНЫ ---
class TemplateCreate(BaseModel):
    name: str; text: str; attach_mode: str; folder_id: int | None = None; media_json: list | None = None; buttons_json: list | None = None

@app.get("/api/templates")
async def get_templates(_=Depends(get_current_admin)):
    async with SessionLocal() as session:
        return [{"id": t.id, "name": t.name, "text": t.text, "mode": t.attach_mode, "folder_id": t.folder_id, "media_json": t.media_json, "buttons_json": t.buttons_json} for t in (await session.execute(select(Template).order_by(Template.id.desc()))).scalars().all()]

@app.post("/api/templates")
async def create_template(data: TemplateCreate, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        t = Template(name=data.name, text=data.text, attach_mode=data.attach_mode, folder_id=data.folder_id, media_json=data.media_json, buttons_json=data.buttons_json)
        session.add(t); await session.commit(); return {"status": "ok", "id": t.id}

@app.patch("/api/templates/{template_id}")
async def update_template(template_id: int, data: TemplateCreate, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        t = (await session.execute(select(Template).where(Template.id == template_id))).scalar_one_or_none()
        if not t: raise HTTPException(status_code=404)
        t.name = data.name; t.text = data.text; t.attach_mode = data.attach_mode
        t.folder_id = data.folder_id; t.media_json = data.media_json; t.buttons_json = data.buttons_json
        await session.commit(); return {"status": "ok"}

@app.delete("/api/templates/{template_id}")
async def delete_template(template_id: int, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        t = (await session.execute(select(Template).where(Template.id == template_id))).scalar_one_or_none()
        if not t: raise HTTPException(status_code=404)
        await session.delete(t); await session.commit(); return {"status": "ok"}

class AttachTemplate(BaseModel):
    template_id: int; mode: str

@app.post("/api/posts/{post_id}/templates")
async def attach_template(post_id: int, data: AttachTemplate, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        stmt = select(PostTemplate).where(PostTemplate.post_id == post_id, PostTemplate.template_id == data.template_id)
        pt = (await session.execute(stmt)).scalar_one_or_none()
        if pt:
            pt.mode = data.mode
        else:
            session.add(PostTemplate(post_id=post_id, template_id=data.template_id, position=0, mode=data.mode))
        await session.commit()
        return {"status": "ok"}

@app.delete("/api/posts/{post_id}/templates/{template_id}")
async def detach_template(post_id: int, template_id: int, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        pt = (await session.execute(select(PostTemplate).where(PostTemplate.post_id == post_id, PostTemplate.template_id == template_id))).scalar_one_or_none()
        if pt: await session.delete(pt); await session.commit()
        return {"status": "ok"}

@app.get("/api/metrics")
async def get_metrics(_=Depends(get_current_admin)):
    async with SessionLocal() as session:
        total = await session.scalar(select(func.count(Post.id))) or 0
        published = await session.scalar(select(func.count(Post.id)).where(Post.status == PostStatus.PUBLISHED)) or 0
        deleted = await session.scalar(select(func.count(Post.id)).where(Post.status == PostStatus.DELETED)) or 0
        pending = await session.scalar(select(func.count(Post.id)).where(Post.status.in_([PostStatus.NEW, PostStatus.SCHEDULED]))) or 0
        stmt = (select(Source.username, func.count(Post.id).label('total'), func.sum(case((Post.status == PostStatus.PUBLISHED, 1), else_=0)).label('published'), func.sum(case((Post.status == PostStatus.DELETED, 1), else_=0)).label('deleted')).join(Post, Post.source_id == Source.id).group_by(Source.id, Source.username))
        sources_stats = []
        for row in await session.execute(stmt):
            pub_s = row.published or 0; del_s = row.deleted or 0
            efficiency = int((pub_s / (pub_s + del_s) * 100)) if (pub_s + del_s) > 0 else 0
            sources_stats.append({"source": f"@{row.username}", "total": row.total, "published": pub_s, "deleted": del_s, "efficiency": efficiency})
        sources_stats.sort(key=lambda x: x["efficiency"], reverse=True)
        return {"summary": {"total": total, "published": published, "deleted": deleted, "pending": pending}, "sources": sources_stats}

# --- ОЧИСТКА КАНАЛА ---
@app.post("/api/target-channel/clear")
async def clear_target_channel_endpoint(_=Depends(get_current_admin)):
    success, msg = await clear_target_channel()
    if success: return {"status": "ok", "message": msg}
    raise HTTPException(status_code=500, detail=msg)