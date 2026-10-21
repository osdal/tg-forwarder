"""Модуль для работы с ИИ (Google Gemini)."""
import base64
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


# --- НОВАЯ ФУНКЦИЯ: генерация изображения по промпту ---
def generate_image(prompt: str) -> bytes:
    """Генерирует изображение по текстовому промпту и возвращает байты PNG."""
    client = get_gemini_client()
    # Модель может отличаться в зависимости от версии google-genai.
    # Актуальные варианты: "gemini-2.5-flash-image" или "imagen-3.0-generate-002".
    response = client.models.generate_images(
        model="gemini-2.5-flash-image",
        prompt=prompt,
        config={"number_of_images": 1},
    )
    # Извлекаем байты первого изображения
    return response.generated_images[0].image.image_bytes