import re
import json
from typing import List, Any

SYSTEM_PROMPT = """Ты генерируешь Python regex паттерны для поиска слов в банковских платёжных назначениях на русском языке.

Правила:
1. Для каждой фразы создай паттерны для ОБОИХ порядков слов.
2. Используй только этот шаблон: r'\\bСТЕМ1\\w{0,3}[-/ ]*СТЕМ2\\w{0,3}\\b'
   - СТЕМ — основа слова (убери окончание, оставь корень)
   - Все символы в нижнем регистре
3. Верни ТОЛЬКО JSON-массив строк без объяснений.

Пример:
Вход: ["Фасадные кассеты", "алюминиевые панели"]
Выход:
[
  "\\\\bфасадн\\\\w{0,3}[-/ ]*кассет\\\\w{0,3}\\\\b",
  "\\\\bкассет\\\\w{0,3}[-/ ]*фасадн\\\\w{0,3}\\\\b",
  "\\\\bалюмини\\\\w{0,3}[-/ ]*панел\\\\w{0,3}\\\\b",
  "\\\\bпанел\\\\w{0,3}[-/ ]*алюмини\\\\w{0,3}\\\\b"
]"""


def generate_regex(product_words: List[str], client: Any) -> List[str]:
    """
    Call Claude to generate regex patterns from product words.
    Each invalid pattern is dropped with a warning.
    Returns empty list if product_words is empty or Claude fails.
    """
    if not product_words:
        return []

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(product_words, ensure_ascii=False)}],
    )

    raw = message.content[0].text.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        patterns = json.loads(raw)
    except json.JSONDecodeError:
        print(f"Warning: regex generator returned invalid JSON. Returning empty list.")
        return []

    valid = []
    for p in patterns:
        try:
            re.compile(p)
            valid.append(p)
        except re.error:
            print(f"Warning: invalid regex pattern dropped: {p!r}")

    return valid
