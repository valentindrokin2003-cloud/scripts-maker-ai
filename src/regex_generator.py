import re
import json
import logging
import time
from typing import List, Any

logger = logging.getLogger(__name__)

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
    Call DeepSeek to generate regex patterns from product words.
    Each invalid pattern is dropped with a warning.
    Returns empty list if product_words is empty or DeepSeek fails.
    """
    if not product_words:
        logger.info(f"[generate_regex] No product words provided, returning empty list")
        return []

    logger.info(f"[generate_regex] Starting API call to DeepSeek")
    logger.info(f"[generate_regex] Input word count: {len(product_words)}")

    user_content = json.dumps(product_words, ensure_ascii=False)
    logger.info(f"[generate_regex] User message length: {len(user_content)} chars")
    logger.debug(f"[generate_regex] Words: {product_words}")

    logger.info(f"[generate_regex] API endpoint: https://api.deepseek.com")
    logger.info(f"[generate_regex] Model: deepseek-chat")
    logger.info(f"[generate_regex] Request timeout: 60 seconds")

    start_time = time.time()
    try:
        logger.debug(f"[generate_regex] Building request payload...")
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
        logger.debug(f"[generate_regex] Payload ready, connecting to API...")
        logger.info(f"[generate_regex] Sending request to API (will wait max 60s)...")

        message = client.chat.completions.create(
            model="deepseek-chat",
            max_tokens=2048,
            timeout=60,
            messages=messages,
        )
        elapsed = time.time() - start_time
        logger.info(f"[generate_regex] ✓ API response received in {elapsed:.2f}s")
        logger.debug(f"[generate_regex] Response choices: {len(message.choices)}")
    except TimeoutError as e:
        elapsed = time.time() - start_time
        logger.error(f"[generate_regex] ✗ API request TIMEOUT after {elapsed:.2f}s (max was 60s)")
        logger.error(f"[generate_regex] This usually means the API is not responding or network is too slow")
        logger.warning(f"[generate_regex] Returning empty list due to timeout")
        return []
    except ConnectionError as e:
        elapsed = time.time() - start_time
        logger.error(f"[generate_regex] ✗ CONNECTION ERROR after {elapsed:.2f}s: {e}")
        logger.error(f"[generate_regex] Check: 1) Internet connection, 2) API endpoint reachability, 3) Firewall/proxy")
        logger.warning(f"[generate_regex] Returning empty list due to connection error")
        return []
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[generate_regex] ✗ API call failed after {elapsed:.2f}s: {type(e).__name__}: {e}")
        logger.warning(f"[generate_regex] Returning empty list due to API failure")
        return []

    raw = message.choices[0].message.content.strip()
    logger.info(f"[generate_regex] Raw response length: {len(raw)} chars")
    logger.debug(f"[generate_regex] Raw response preview: {raw[:100]}...")

    if raw.startswith("```"):
        logger.debug(f"[generate_regex] Detected markdown code fence, stripping...")
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
        logger.debug(f"[generate_regex] After stripping: {len(raw)} chars")

    try:
        patterns = json.loads(raw)
        logger.info(f"[generate_regex] JSON parsed successfully")
        logger.info(f"[generate_regex] Total patterns from API: {len(patterns)}")
    except json.JSONDecodeError as e:
        logger.error(f"[generate_regex] JSON parsing failed: {e}")
        logger.debug(f"[generate_regex] Raw content preview: {raw[:200]}")
        logger.warning(f"[generate_regex] Returning empty list due to invalid JSON")
        return []

    valid = []
    for i, p in enumerate(patterns):
        try:
            re.compile(p)
            valid.append(p)
        except re.error as e:
            logger.warning(f"[generate_regex] Invalid regex pattern at index {i} dropped: {p!r} (error: {e})")

    logger.info(f"[generate_regex] Final valid patterns: {len(valid)}/{len(patterns)}")
    return valid
