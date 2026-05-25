"""Stage 1: LLM extracts a semantic spec from product words.

The LLM acts as a morphological analyser: it identifies concepts,
their POS tags, and co-occurrence pairs. The resulting dict is passed
directly to Stage 2 (regex_builder_stage2.build_regex_from_spec).
"""
import json
import logging
import time
from typing import Any, Dict, List, Optional

from src.llm_json import LLMJsonError, parse_llm_json
from src.settings import DEFAULT_LLM_MODEL

logger = logging.getLogger(__name__)

SPEC_PROMPT = r"""Ты выделяешь семантические концепты из русских брифов для поиска банковских платёжных назначений.

По списку продуктовых слов/фраз верни JSON-объект {"concepts": [...]}.

Правила:
1. ТОЛЬКО JSON-объект — без пояснений, без markdown.
2. Каждый концепт — объект с полями:
   - "base_word": базовая форма (именительный падеж, единственное число).
     Прилагательные — мужской род: "бухгалтерский" ✓, "бухгалтерские" ✗
   - "pos": "adj" (прилагательное) | "noun" (существительное) | "brand" (бренд/аббревиатура/код)
   - "standalone": true если слово осмысленно искать в тексте без спутника; false для прилагательных
   - "ambiguous": true если основа слова (после снятия именительного окончания) короткая или
     является префиксом несвязанных слов — тогда свободное окончание \w{0,4} даёт ложные
     срабатывания. Примеры: "сыр" → true (сыр → сырьё, сырой), "лот" → true (лот → лотерея),
     "пар" → true (пар → партнёр). Большинство слов — false.
   - "pairs": список {"with": "<base_word другого концепта>"} — слова, которые стоят рядом в платежах
3. Многословная фраза → несколько концептов + связи через pairs.
4. Синонимы к одному слову → несколько pairs у одного концепта.
5. Бренды, аббревиатуры, латинские коды: pos="brand", standalone=true, pairs=[].
6. Слишком общие слова ("услуга", "товар", "материал") без прилагательного: standalone=false.
7. pairs однонаправленные: если A уже перечислил B в своих pairs — не добавляй A в pairs концепта B.
   Обратный порядок (B+A) генерируется автоматически.

Пример:
Вход: ["бухгалтерские услуги", "консалтинговые услуги", "аутсорсинг бухгалтерии"]
Выход:
{
  "concepts": [
    {"base_word": "бухгалтерский", "pos": "adj", "standalone": false, "ambiguous": false,
     "pairs": [{"with": "услуга"}, {"with": "аутсорсинг"}]},
    {"base_word": "консалтинговый", "pos": "adj", "standalone": false, "ambiguous": false,
     "pairs": [{"with": "услуга"}]},
    {"base_word": "услуга", "pos": "noun", "standalone": false, "ambiguous": false, "pairs": []},
    {"base_word": "аутсорсинг", "pos": "noun", "standalone": true, "ambiguous": false, "pairs": []}
  ]
}

Пример 2:
Вход: ["выездные семинары", "корпоративы", "конференции", "сыры", "молочная продукция"]
Выход:
{
  "concepts": [
    {"base_word": "выездной", "pos": "adj", "standalone": false, "ambiguous": false,
     "pairs": [{"with": "семинар"}, {"with": "корпоратив"}, {"with": "конференция"}]},
    {"base_word": "семинар", "pos": "noun", "standalone": false, "ambiguous": false, "pairs": []},
    {"base_word": "корпоратив", "pos": "noun", "standalone": true, "ambiguous": false, "pairs": []},
    {"base_word": "конференция", "pos": "noun", "standalone": true, "ambiguous": false, "pairs": []},
    {"base_word": "сыр", "pos": "noun", "standalone": true, "ambiguous": true, "pairs": []},
    {"base_word": "молочный", "pos": "adj", "standalone": false, "ambiguous": false,
     "pairs": [{"with": "продукция"}]},
    {"base_word": "продукция", "pos": "noun", "standalone": false, "ambiguous": false, "pairs": []}
  ]
}"""


def extract_spec(
    product_words: List[str],
    client: Any,
    model: str = DEFAULT_LLM_MODEL,
) -> Optional[Dict]:
    """Call the LLM to extract a semantic spec from product words.

    Returns a validated spec dict, or None on any failure (network,
    invalid JSON, missing 'concepts' key).
    """
    user_content = json.dumps(product_words, ensure_ascii=False)
    logger.info("[extract_spec] Requesting spec for %d words", len(product_words))

    start = time.time()
    try:
        message = client.chat.completions.create(
            model=model,
            max_tokens=1024,
            timeout=60,
            messages=[
                {"role": "system", "content": SPEC_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )
        elapsed = time.time() - start
        logger.info("[extract_spec] Response received in %.2fs", elapsed)
    except Exception as e:
        elapsed = time.time() - start
        logger.error("[extract_spec] API error after %.2fs: %s: %s", elapsed, type(e).__name__, e)
        return None

    raw = message.choices[0].message.content.strip()
    logger.debug("[extract_spec] Raw: %s", raw[:300])

    try:
        parsed = parse_llm_json(raw)
    except LLMJsonError as e:
        logger.error("[extract_spec] JSON parse error: %s", e)
        return None

    if not isinstance(parsed, dict) or "concepts" not in parsed:
        logger.warning("[extract_spec] Response is not a valid spec (missing 'concepts')")
        return None

    concepts = parsed.get("concepts", [])
    logger.info("[extract_spec] Extracted %d concepts", len(concepts))
    return parsed
