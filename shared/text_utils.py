"""Утилиты для работы с текстом."""

import re

def remove_links(text: str) -> str:
    """Удаляет все ссылки из текста."""
    if not text:
        return ""
    
    # Регулярное выражение для поиска URL (http/https, www, t.me)
    url_pattern = re.compile(r'(https?://\S+|www\.\S+|t\.me/\S+)')
    
    # Заменяем найденные ссылки на пустую строку
    cleaned = url_pattern.sub('', text)
    
    # Убираем лишние пустые строки, которые могли остаться
    cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned).strip()
    
    return cleaned