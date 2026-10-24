"""FastAPI backend для веб-панели."""
import io
import os
import time
import uuid
import hmac
import hashlib
import jwt
import base64
import json
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from fastapi import FastAPI, HTTPException, File, UploadFile, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select, func, case
from sqlalchemy.orm import selectinload
from telethon import TelegramClient
from telethon.sessions import StringSession

from shared.config import get_settings, license_info, LicenseInfo, DEFAULT_PLANS
from shared.db import SessionLocal
from shared.models import Post, PostStatus, PostMedia, Template, PostTemplate, TemplateFolder, Source, SourceTemplate, MediaLibrary, AppSettings, ClientLicense
from shared.publisher import publish_post_to_channel
from shared.minio_client import get_minio
from shared.ai_helper import translate_text, rewrite_text, generate_text, generate_image, list_image_models
from shared.pipeline import apply_pipeline
from shared.text_utils import remove_links
from scripts.refetch_media import refetch_post_media
from scripts.clear_target_channel import clear_target_channel

settings = get_settings()
app = FastAPI(title="TG Forwarder Web API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
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

def get_effective_license(x_view_as: str | None = None) -> LicenseInfo:
    if license_info.plan == "owner" and x_view_as in DEFAULT_PLANS:
        return LicenseInfo(f"Owner (View As {x_view_as})", datetime.now() + timedelta(days=1), x_view_as, DEFAULT_PLANS[x_view_as])
    return license_info

def get_current_owner(x_view_as: str = Header(None), _=Depends(get_current_admin)):
    lic = get_effective_license(x_view_as)
    if lic.plan != "owner":
        raise HTTPException(status_code=403, detail="Доступно только для владельца.")
    return True

def check_ai_enabled(lic: LicenseInfo):
    if not lic.get("ai_enabled"):
        raise HTTPException(status_code=403, detail="AI-функции недоступны в вашем тарифе.")

def check_image_gen(lic: LicenseInfo):
    if not lic.get("image_gen_enabled"):
        raise HTTPException(status_code=403, detail="Генерация картинок недоступна в вашем тарифе.")

# --- НАСТРОЙКИ И КЛЮЧ GEMINI ---
class GeminiKeyUpdate(BaseModel):
    api_key: str

class GeminiTestRequest(BaseModel):
    api_key: str

@app.get("/api/settings")
async def get_settings_api(_=Depends(get_current_admin)):
    async with SessionLocal() as session:
        s = (await session.execute(select(AppSettings).where(AppSettings.id == 1))).scalar_one_or_none()
        return {"gemini_api_key": s.gemini_api_key if s else ""}

@app.post("/api/settings/gemini")
async def save_gemini_key(data: GeminiKeyUpdate, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        s = (await session.execute(select(AppSettings).where(AppSettings.id == 1))).scalar_one_or_none()
        if not s:
            s = AppSettings(id=1, gemini_api_key=data.api_key)
            session.add(s)
        else:
            s.gemini_api_key = data.api_key
        await session.commit()
    return {"status": "ok"}

@app.post("/api/settings/gemini/test")
async def test_gemini_key(data: GeminiTestRequest, _=Depends(get_current_admin)):
    try:
        res = translate_text("Hello, world!", api_key=data.api_key)
        return {"status": "ok", "message": f"Ключ работает. Тестовый перевод: {res}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- ЦЕПОЧКИ (PIPELINE) ---
class PipelineUpdate(BaseModel):
    steps: list

@app.patch("/api/sources/{source_id}/pipeline")
async def update_source_pipeline(source_id: int, data: PipelineUpdate, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        source = (await session.execute(select(Source).where(Source.id == source_id))).scalar_one_or_none()
        if not source: raise HTTPException(status_code=404, detail="Источник не найден")
        source.pipeline_json = json.dumps(data.steps)
        await session.commit()
    return {"status": "ok"}

@app.post("/api/posts/{post_id}/run-pipeline")
async def run_post_pipeline(post_id: int, x_view_as: str = Header(None), _=Depends(get_current_admin)):
    lic = get_effective_license(x_view_as)
    async with SessionLocal() as session:
        post = (await session.execute(select(Post).where(Post.id == post_id).options(selectinload(Post.source), selectinload(Post.media)))).scalar_one_or_none()
        if not post: raise HTTPException(status_code=404, detail="Пост не найден")
        
        app_settings = (await session.execute(select(AppSettings).where(AppSettings.id == 1))).scalar_one_or_none()
        gemini_key = app_settings.gemini_api_key if app_settings else None
        
        source = post.source
        current_text = post.edited_text or post.original_text or ""
        
        new_text, new_media = apply_pipeline(
            current_text, 
            source.pipeline_json, 
            api_key=gemini_key, 
            ai_enabled=lic.get("ai_enabled", False)
        )
        
        post.edited_text = new_text
        post.pipeline_applied = True
        
        start_order = len(post.media)
        for i, m in enumerate(new_media):
            session.add(PostMedia(post_id=post.id, minio_key=m["key"], media_type=m["type"], order=start_order + i, is_user_added=True))
            
        await session.commit()
        return {"status": "ok"}

# --- УПРАВЛЕНИЕ ЛИЦЕНЗИЯМИ (ТОЛЬКО ДЛЯ OWNER) ---
class LicenseCreate(BaseModel):
    client_name: str
    plan: str
    days: int

@app.get("/api/admin/download-latest")
async def download_latest(_=Depends(get_current_owner)):
    file_path = "/app/landing/latest.zip"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Архив ещё не собран.")
    return FileResponse(path=file_path, filename="tg-forwarder.zip", media_type="application/zip")

@app.get("/api/admin/licenses")
async def get_licenses(_=Depends(get_current_owner)):
    async with SessionLocal() as session:
        result = await session.execute(select(ClientLicense).order_by(ClientLicense.id.desc()))
        return [{"id": l.id, "client_name": l.client_name, "plan": l.plan, "expires_at": l.expires_at.isoformat(), "is_active": l.is_active, "license_key": l.license_key} for l in result.scalars().all()]

@app.post("/api/admin/licenses")
async def create_license(data: LicenseCreate, _=Depends(get_current_owner)):
    if not settings.license_private_key: raise HTTPException(status_code=500, detail="Приватный ключ не настроен.")
    if data.plan not in DEFAULT_PLANS: raise HTTPException(status_code=400, detail="Неверный тариф.")
    try:
        private_key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(settings.license_private_key))
        expires = (datetime.now() + timedelta(days=data.days)).isoformat()
        payload = {"client": data.client_name, "expires": expires, "plan": data.plan, "limits": DEFAULT_PLANS[data.plan]}
        payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode()
        signature = private_key.sign(payload_b64.encode())
        signature_b64 = base64.b64encode(signature).decode()
        lic_key = f"{payload_b64}.{signature_b64}"
        
        async with SessionLocal() as session:
            l = ClientLicense(client_name=data.client_name, license_key=lic_key, plan=data.plan, expires_at=datetime.fromisoformat(expires))
            session.add(l); await session.commit()
            return {"status": "ok", "license_key": lic_key}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/admin/licenses/{lic_id}/toggle")
async def toggle_license(lic_id: int, _=Depends(get_current_owner)):
    async with SessionLocal() as session:
        l = (await session.execute(select(ClientLicense).where(ClientLicense.id == lic_id))).scalar_one_or_none()
        if not l: raise HTTPException(status_code=404)
        l.is_active = not l.is_active; await session.commit()
        return {"status": "ok", "is_active": l.is_active}

@app.delete("/api/admin/licenses/{lic_id}")
async def delete_license(lic_id: int, _=Depends(get_current_owner)):
    async with SessionLocal() as session:
        l = (await session.execute(select(ClientLicense).where(ClientLicense.id == lic_id))).scalar_one_or_none()
        if not l: raise HTTPException(status_code=404)
        await session.delete(l); await session.commit()
        return {"status": "ok"}

# --- ОСТАЛЬНЫЕ ЭНДПОИНТЫ ---
@app.get("/api/license/info")
async def get_license_info(x_view_as: str = Header(None), _=Depends(get_current_admin)):
    return get_effective_license(x_view_as).to_dict()

@app.get("/api/status")
async def get_status(_=Depends(get_current_admin)):
    async with SessionLocal() as session:
        s = (await session.execute(select(AppSettings).where(AppSettings.id == 1))).scalar_one_or_none()
        naive_now = datetime.now(timezone.utc).replace(tzinfo=None)
        bot_online = False; collector_online = False
        if s:
            if s.bot_last_seen and (naive_now - s.bot_last_seen).total_seconds() < 30: bot_online = True
            if s.collector_last_seen and (naive_now - s.collector_last_seen).total_seconds() < 30: collector_online = True
        return {"bot_online": bot_online, "collector_online": collector_online}

class AITextRequest(BaseModel): text: str; word_count: int | None = None
class AIGenerateRequest(BaseModel): prompt: str; base_text: str | None = None
class AIImageRequest(BaseModel): prompt: str; post_id: int | None = None; width: int = 1024; height: int = 1024; model: str = "flux"; seed: int | None = None; nologo: bool = True

@app.post("/api/ai/translate")
async def api_translate(data: AITextRequest, x_view_as: str = Header(None), _=Depends(get_current_admin)):
    lic = get_effective_license(x_view_as)
    check_ai_enabled(lic)
    async with SessionLocal() as session:
        s = (await session.execute(select(AppSettings).where(AppSettings.id == 1))).scalar_one_or_none()
        key = s.gemini_api_key if s else None
    try: return {"result": translate_text(data.text, api_key=key)}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/rewrite")
async def api_rewrite(data: AITextRequest, x_view_as: str = Header(None), _=Depends(get_current_admin)):
    lic = get_effective_license(x_view_as)
    check_ai_enabled(lic)
    async with SessionLocal() as session:
        s = (await session.execute(select(AppSettings).where(AppSettings.id == 1))).scalar_one_or_none()
        key = s.gemini_api_key if s else None
    try: return {"result": rewrite_text(data.text, data.word_count, api_key=key)}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/remove-links")
async def api_remove_links(data: AITextRequest, _=Depends(get_current_admin)):
    try: return {"result": remove_links(data.text)}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/generate")
async def api_generate(data: AIGenerateRequest, x_view_as: str = Header(None), _=Depends(get_current_admin)):
    lic = get_effective_license(x_view_as)
    check_ai_enabled(lic)
    async with SessionLocal() as session:
        s = (await session.execute(select(AppSettings).where(AppSettings.id == 1))).scalar_one_or_none()
        key = s.gemini_api_key if s else None
    try: return {"result": generate_text(data.prompt, data.base_text or "", api_key=key)}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ai/image-models")
async def api_image_models(x_view_as: str = Header(None), _=Depends(get_current_admin)):
    lic = get_effective_license(x_view_as)
    check_image_gen(lic)
    try: return {"models": list_image_models()}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/generate-image")
async def api_generate_image(data: AIImageRequest, x_view_as: str = Header(None), _=Depends(get_current_admin)):
    lic = get_effective_license(x_view_as)
    check_image_gen(lic)
    try:
        image_bytes = generate_image(data.prompt, width=data.width, height=data.height, model=data.model, seed=data.seed, nologo=data.nologo)
    except Exception as e: raise HTTPException(status_code=500, detail=f"Ошибка генерации: {str(e)}")

    if not data.post_id:
        key = f"library/ai_{uuid.uuid4().hex[:8]}.jpg"
        get_minio().upload_bytes(key, image_bytes, content_type="image/jpeg", tags={"keep": "true"})
        async with SessionLocal() as session:
            m = MediaLibrary(minio_key=key, media_type="photo", original_name="ai_generated")
            session.add(m); await session.commit()
            return {"status": "ok", "media_id": m.id, "key": key}

    async with SessionLocal() as session:
        post = (await session.execute(select(Post).where(Post.id == data.post_id).options(selectinload(Post.media)))).scalar_one_or_none()
        if not post: raise HTTPException(status_code=404)
        minio_key = f"user/{data.post_id}_ai_{uuid.uuid4().hex[:6]}.jpg"
        get_minio().upload_bytes(minio_key, image_bytes, content_type="image/jpeg", tags={"keep": "true"})
        pm = PostMedia(post_id=post.id, minio_key=minio_key, media_type="photo", order=len(post.media), is_user_added=True)
        session.add(pm); await session.commit()
        return {"status": "ok", "media_id": pm.id, "minio_key": minio_key}

class TelegramAuthData(BaseModel):
    id: int; first_name: str | None = None; last_name: str | None = None; username: str | None = None; photo_url: str | None = None; auth_date: int; hash: str
class DevLoginData(BaseModel): password: str

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

@app.get("/api/sources")
async def get_sources(_=Depends(get_current_admin)):
    async with SessionLocal() as session:
        result = await session.execute(select(Source).options(selectinload(Source.templates).selectinload(SourceTemplate.template)).order_by(Source.id))
        return [{"id": s.id, "telegram_id": s.telegram_id, "title": s.title, "username": s.username, "enabled": s.enabled, "auto_publish": s.auto_publish, "auto_template_id": s.auto_template_id, "pipeline_json": s.pipeline_json, "templates": [{"id": st.template.id, "name": st.template.name} for st in s.templates]} for s in result.scalars().all()]

class SourceCreate(BaseModel): channel_input: str

@app.post("/api/sources")
async def add_source(data: SourceCreate, x_view_as: str = Header(None), _=Depends(get_current_admin)):
    lic = get_effective_license(x_view_as)
    max_sources = lic.get("max_sources", 5)
    if max_sources != -1:
        async with SessionLocal() as session:
            count = await session.scalar(select(func.count(Source.id)))
            if count >= max_sources: raise HTTPException(status_code=403, detail=f"Достигнут лимит источников для тарифа '{lic.plan}' ({max_sources}).")
    
    clean_input = data.channel_input.strip(); is_numeric_id = False
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

class AutoPublishUpdate(BaseModel): auto_publish: bool; auto_template_id: int | None = None

@app.patch("/api/sources/{source_id}/auto-publish")
async def update_auto_publish(source_id: int, data: AutoPublishUpdate, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        source = (await session.execute(select(Source).where(Source.id == source_id))).scalar_one_or_none()
        if not source: raise HTTPException(status_code=404)
        source.auto_publish = data.auto_publish; source.auto_template_id = data.auto_template_id
        await session.commit(); return {"status": "ok"}

@app.delete("/api/sources/{source_id}")
async def delete_source(source_id: int, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        source = (await session.execute(select(Source).where(Source.id == source_id))).scalar_one_or_none()
        if not source: raise HTTPException(status_code=404)
        await session.delete(source); await session.commit(); return {"status": "ok"}

class AttachSourceTemplate(BaseModel): template_id: int

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

@app.post("/api/upload")
async def upload_generic_media(file: UploadFile = File(...), _=Depends(get_current_admin)):
    data = await file.read(); ext = file.filename.split('.')[-1].lower() if file.filename and '.' in file.filename else "jpg"
    if ext not in ("jpg", "jpeg", "png", "webp", "gif", "mp4"): ext = "jpg"
    key = f"templates/{uuid.uuid4().hex[:8]}.{ext}"
    get_minio().upload_bytes(key, data, content_type=file.content_type or "image/jpeg", tags={"keep": "true"})
    return {"key": key, "type": "video" if ext == "mp4" else "photo"}

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
        if not pm: raise HTTPException(status_code=404)
        try: data = get_minio().download_bytes(pm.minio_key)
        except Exception: raise HTTPException(status_code=404)
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

@app.get("/")
def read_root(): return {"status": "ok"}

@app.get("/api/posts")
async def get_posts(trash: bool = False, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        query = select(Post).options(selectinload(Post.source), selectinload(Post.media), selectinload(Post.templates).selectinload(PostTemplate.template))
        if trash: query = query.where(Post.status == PostStatus.DELETED).order_by(Post.deleted_at.desc())
        else: query = query.where(Post.status != PostStatus.DELETED).order_by(Post.id.desc())
        result = await session.execute(query.limit(100))
        return [{"id": p.id, "source": p.source.username if p.source else None, "text": p.edited_text or p.original_text, "status": p.status, "created_at": p.created_at.isoformat() if p.created_at else None, "media_count": len(p.media), "media": [{"id": m.id, "type": m.media_type, "key": m.minio_key} for m in p.media], "templates": [{"id": pt.template.id, "name": pt.template.name, "mode": pt.mode or pt.template.attach_mode} for pt in p.templates], "buttons_json": p.buttons_json, "pipeline_applied": p.pipeline_applied} for p in result.scalars().all()]

@app.post("/api/manual-post")
async def create_manual_post(_=Depends(get_current_admin)):
    async with SessionLocal() as session:
        try:
            source = (await session.execute(select(Source).where(Source.username == "manual"))).scalar_one_or_none()
            if not source:
                source = Source(telegram_id=-999999999, title="Ручной пост", username="manual", enabled=False)
                session.add(source); await session.commit(); await session.refresh(source)
            msg_id = -int(time.time() * 1000) - int(uuid.uuid4().int % 1000)
            post = Post(source_id=source.id, source_message_id=msg_id, original_text="", status=PostStatus.NEW, notified=True)
            session.add(post); await session.commit(); await session.refresh(post)
            return {"status": "ok", "id": post.id}
        except Exception as e: await session.rollback(); raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/posts/{post_id}")
async def get_single_post(post_id: int, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        result = await session.execute(select(Post).where(Post.id == post_id).options(selectinload(Post.source), selectinload(Post.media), selectinload(Post.templates).selectinload(PostTemplate.template)))
        p = result.scalar_one_or_none()
        if not p: raise HTTPException(status_code=404)
        return {"id": p.id, "source": p.source.username if p.source else None, "text": p.edited_text or p.original_text, "status": p.status, "media_count": len(p.media), "media": [{"id": m.id, "type": m.media_type, "key": m.minio_key} for m in p.media], "templates": [{"id": pt.template.id, "name": pt.template.name, "mode": pt.mode or pt.template.attach_mode} for pt in p.templates], "buttons_json": p.buttons_json, "pipeline_applied": p.pipeline_applied}

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
        post.status = PostStatus.DELETED; post.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
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

class PostUpdate(BaseModel): text: str; buttons_json: list | None = None

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

class FolderCreate(BaseModel): name: str

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

class AttachTemplate(BaseModel): template_id: int; mode: str

@app.post("/api/posts/{post_id}/templates")
async def attach_template(post_id: int, data: AttachTemplate, _=Depends(get_current_admin)):
    async with SessionLocal() as session:
        stmt = select(PostTemplate).where(PostTemplate.post_id == post_id, PostTemplate.template_id == data.template_id)
        pt = (await session.execute(stmt)).scalar_one_or_none()
        if pt: pt.mode = data.mode
        else: session.add(PostTemplate(post_id=post_id, template_id=data.template_id, position=0, mode=data.mode))
        await session.commit(); return {"status": "ok"}

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

@app.post("/api/target-channel/clear")
async def clear_target_channel_endpoint(_=Depends(get_current_admin)):
    success, msg = await clear_target_channel()
    if success: return {"status": "ok", "message": msg}
    raise HTTPException(status_code=500, detail=msg)