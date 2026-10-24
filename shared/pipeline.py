import json
import uuid
import logging
from shared.ai_helper import translate_text, rewrite_text, generate_text, generate_image
from shared.text_utils import remove_links
from shared.minio_client import get_minio

log = logging.getLogger("pipeline")

def apply_pipeline(text: str, steps_json: str | None, api_key: str | None = None, ai_enabled: bool = True) -> tuple[str, list[dict]]:
    """
    Выполняет цепочку шагов над текстом.
    Возвращает: (новый_текст, список_новых_медиа_файлов)
    """
    if not steps_json:
        return text, []
    
    try:
        steps = json.loads(steps_json)
    except Exception:
        log.error("Неверный формат JSON в pipeline_json")
        return text, []
        
    current_text = text or ""
    new_media = []
    
    # Шаги, требующие ИИ
    AI_STEPS = ["translate", "rewrite", "generate_text"]
    
    for step in steps:
        step_type = step.get("type")
        params = step.get("params", {})
        
        if step_type in AI_STEPS and not ai_enabled:
            log.warning(f"Пропущен шаг {step_type}: ИИ недоступен на этом тарифе.")
            continue
            
        try:
            if step_type == "remove_links":
                current_text = remove_links(current_text)
            elif step_type == "translate":
                current_text = translate_text(current_text, api_key=api_key)
            elif step_type == "rewrite":
                word_count = params.get("words")
                current_text = rewrite_text(current_text, word_count=word_count, api_key=api_key)
            elif step_type == "generate_text":
                prompt = params.get("prompt", "")
                current_text = generate_text(prompt, base_text=current_text, api_key=api_key)
            elif step_type == "generate_image":
                prompt = params.get("prompt", "")
                width = params.get("width", 1080)
                height = params.get("height", 1080)
                if prompt:
                    image_bytes = generate_image(prompt, width=width, height=height)
                    minio_key = f"pipeline/{uuid.uuid4().hex[:8]}.jpg"
                    get_minio().upload_bytes(minio_key, image_bytes, content_type="image/jpeg", tags={"keep": "true"})
                    new_media.append({"key": minio_key, "type": "photo"})
        except Exception as e:
            log.error(f"Ошибка в шаге {step_type}: {e}")
            continue
            
    return current_text, new_media