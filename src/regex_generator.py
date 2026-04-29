import json
import logging
import time
from typing import List, Any

from src.llm_json import LLMJsonError, parse_llm_json
from src.regex_builder import build_local_regex, validate_regex_patterns
from src.settings import DEFAULT_LLM_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты генерируешь Python regex паттерны для поиска товаров и услуг в банковских платёжных назначениях на русском языке.

Правила:
1. Верни ТОЛЬКО JSON-массив строк без объяснений.
2. Пиши Python regex без флага re.IGNORECASE, все кириллические основы в нижнем регистре.
3. Используй границы слов \\b и разделитель [-/ ]* между словами.
4. Для составных фраз обычно создавай прямой и обратный порядок слов.
5. Добавляй необязательные предлоги только между товаром и назначением: (?:для|к|на|с|из|от|в|по|за)?.
6. Для окончаний используй \\w{0,1}, \\w{0,2}, \\w{0,3} или \\w*. Не используй синтаксис \\w{,3}.
7. Учитывай типичные опечатки и варианты: е/ё, и/е, одна/две согласные, слитно/через дефис/пробел.
8. Для брендов, аббревиатур и коротких кодов делай отдельные точные паттерны: \\becolab\\b, \\bза[-/ ]*лодм\\b.
9. Не делай чрезмерно широкие паттерны по словам "услуга", "товар", "материал", "изделие" без товарного уточнения.

Пример:
Вход: ["Фасадные кассеты", "алюминиевые панели"]
Выход:
[
  "\\\\bфасадн\\\\w{0,3}[-/ ]*кассет\\\\w{0,3}\\\\b",
  "\\\\bкассет\\\\w{0,3}[-/ ]*фасадн\\\\w{0,3}\\\\b",
  "\\\\bалюмини\\\\w{0,3}[-/ ]*панел\\\\w{0,3}\\\\b",
  "\\\\bпанел\\\\w{0,3}[-/ ]*алюмини\\\\w{0,3}\\\\b"
]"""


def _merge_patterns(*groups: List[str]) -> List[str]:
    merged = []
    seen = set()
    for group in groups:
        for pattern in validate_regex_patterns(group):
            if pattern not in seen:
                seen.add(pattern)
                merged.append(pattern)
    return merged


def generate_regex(
    product_words: List[str],
    client: Any,
    model: str = DEFAULT_LLM_MODEL,
) -> List[str]:
    """
    Call DeepSeek to generate regex patterns from product words.
    Each invalid pattern is dropped with a warning.
    Returns empty list if product_words is empty or DeepSeek fails.
    """
    if not product_words:
        logger.info(f"[generate_regex] No product words provided, returning empty list")
        return []

    local_patterns = build_local_regex(product_words)
    logger.info(f"[generate_regex] Local seed patterns: {len(local_patterns)}")

    logger.info(f"[generate_regex] Starting API call to DeepSeek")
    logger.info(f"[generate_regex] Input word count: {len(product_words)}")

    user_content = json.dumps(product_words, ensure_ascii=False)
    logger.info(f"[generate_regex] User message length: {len(user_content)} chars")
    logger.debug(f"[generate_regex] Words: {product_words}")

    logger.info(f"[generate_regex] API endpoint: https://api.deepseek.com")
    logger.info(f"[generate_regex] Model: {model}")
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
            model=model,
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
        logger.warning(f"[generate_regex] Returning local seed patterns due to timeout")
        return local_patterns
    except ConnectionError as e:
        elapsed = time.time() - start_time
        logger.error(f"[generate_regex] ✗ CONNECTION ERROR after {elapsed:.2f}s: {e}")
        logger.error(f"[generate_regex] Check: 1) Internet connection, 2) API endpoint reachability, 3) Firewall/proxy")
        logger.warning(f"[generate_regex] Returning local seed patterns due to connection error")
        return local_patterns
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[generate_regex] ✗ API call failed after {elapsed:.2f}s: {type(e).__name__}: {e}")
        logger.warning(f"[generate_regex] Returning local seed patterns due to API failure")
        return local_patterns

    raw = message.choices[0].message.content.strip()
    logger.info(f"[generate_regex] Raw response length: {len(raw)} chars")
    logger.debug(f"[generate_regex] Raw response preview: {raw[:100]}...")

    try:
        patterns = parse_llm_json(raw)
        logger.info(f"[generate_regex] JSON parsed successfully")
        logger.info(f"[generate_regex] Total patterns from API: {len(patterns)}")
    except LLMJsonError as e:
        logger.error(f"[generate_regex] JSON parsing failed: {e}")
        logger.debug(f"[generate_regex] Raw content preview: {raw[:200]}")
        logger.warning(f"[generate_regex] Returning local seed patterns due to invalid JSON")
        return local_patterns

    if not isinstance(patterns, list):
        logger.warning(f"[generate_regex] Expected JSON array, got {type(patterns).__name__}")
        return local_patterns

    valid_llm_patterns = []
    for i, pattern in enumerate(patterns):
        valid_pattern = validate_regex_patterns([pattern])
        if valid_pattern:
            valid_llm_patterns.extend(valid_pattern)
        else:
            logger.warning(f"[generate_regex] Invalid regex pattern at index {i} dropped: {pattern!r}")

    merged = _merge_patterns(local_patterns, valid_llm_patterns)
    logger.info(
        "[generate_regex] Final valid patterns: "
        f"{len(merged)} ({len(local_patterns)} local, {len(valid_llm_patterns)} LLM)"
    )
    return merged
