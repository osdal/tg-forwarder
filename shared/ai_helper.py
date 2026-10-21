"""Модуль для работы с ИИ (Google Gemini + бесплатная генерация картинок)."""
import base64
import urllib.parse
import httpx
from google import genai
from shared.config import get_settings

settings = get_settings()


def get_gemini_client():
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY не задан в .env")
    return genai.Client(api_key=settings.gemini_api_key)


def translate_text(text: str) -> str:
    client = get_gemini_client()
    prompt = (
        f"Переведи следующий текст на русский язык. Сохрани оригинальный смысл, "
        f"эмодзи и форматирование. Выведи только готовый текст без лишних комментариев:\n\n{text}"
    )
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    return response.text.strip()


def rewrite_text(text: str, word_count: int | None = None) -> str:
    client = get_gemini_client()
    count_hint = (
        f"Объем должен быть примерно {word_count} слов."
        if word_count
        else "Объем текста сохрани примерно таким же, как в оригинале."
    )
    prompt = (
        f"Сделай рерайт следующего текста. Сохрани все ссылки, смысл и эмодзи. "
        f"Измени формулировки, чтобы текст стал уникальным. {count_hint} "
        f"Выведи только готовый текст без лишних комментариев:\n\n{text}"
    )
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    return response.text.strip()


def generate_text(prompt: str, base_text: str = "") -> str:
    """Генерирует текст по промпту. Если передан base_text — использует его как контекст."""
    client = get_gemini_client()
    if base_text and base_text.strip():
        full_prompt = (
            f"На основе исходного текста и инструкции сгенерируй новый текст на русском языке. "
            f"Сохрани смысл, ссылки и эмодзи, если они уместны.\n\n"
            f"Исходный текст:\n{base_text}\n\n"
            f"Инструкция: {prompt}\n\n"
            f"Выведи только готовый текст без лишних комментариев."
        )
    else:
        full_prompt = (
            f"Сгенерируй текст на русском языке по следующему запросу. "
            f"Оформи его как готовый пост для Telegram (абзацы, эмодзи по смыслу). "
            f"Выведи только готовый текст без лишних комментариев:\n\n{prompt}"
        )
    response = client.models.generate_content(model='gemini-2.5-flash', contents=full_prompt)
    return response.text.strip()


# --- ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ (POLLINATIONS) ---

def generate_image(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    model: str = "flux",
    seed: int | None = None,
    nologo: bool = True,
) -> bytes:
    """Генерирует изображение через Pollinations.ai.

    Параметры:
      width, height — размер в пикселях.
      model — "flux" (качество) или "turbo" (быстро).
      seed — для воспроизводимости (если None — случайный).
      nologo — убрать водяной знак (может не работать без токена).
    """
    encoded_prompt = urllib.parse.quote(prompt, safe='')
    params = {
        "width": width,
        "height": height,
        "model": model,
        "nologo": "true" if nologo else "false",
    }
    if seed is not None:
        params["seed"] = seed
    query = urllib.parse.urlencode(params)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?{query}"

    with httpx.Client(timeout=90.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.content


def list_image_models() -> list[str]:
    """Возвращает список доступных моделей Pollinations."""
    with httpx.Client(timeout=30.0) as client:
        resp = client.get("https://image.pollinations.ai/models")
        resp.raise_for_status()
        return resp.json()