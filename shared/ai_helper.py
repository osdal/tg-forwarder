"""Модуль для работы с ИИ (Google Gemini)."""

from google import genai
from shared.config import get_settings

settings = get_settings()

def get_gemini_client():
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY не задан в .env")
    return genai.Client(api_key=settings.gemini_api_key)

def translate_text(text: str) -> str:
    client = get_gemini_client()
    prompt = f"Переведи следующий текст на русский язык. Сохрани оригинальный смысл, эмодзи и форматирование. Выведи только готовый текст без лишних комментариев:\n\n{text}"
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    return response.text.strip()

def rewrite_text(text: str, word_count: int | None = None) -> str:
    client = get_gemini_client()
    count_hint = f"Объем должен быть примерно {word_count} слов." if word_count else "Объем текста сохрани примерно таким же, как в оригинале."
    prompt = f"Сделай рерайт следующего текста. Сохрани все ссылки, смысл и эмодзи. Измени формулировки, чтобы текст стал уникальным. {count_hint} Выведи только готовый текст без лишних комментариев:\n\n{text}"
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    return response.text.strip()