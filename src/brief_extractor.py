import json
import logging
import time
from typing import Any
from src.models import BriefData

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты парсишь Excel-бриф на B2B подбор клиентов.
Структура файла может быть любой — строки, таблицы, произвольный формат.
Извлеки все поля и верни ТОЛЬКО валидный JSON без дополнительных пояснений.

Схема ответа:
{
  "name": "строка — название компании заказчика",
  "inn_client": ["список ИНН заказчика"],
  "analysis_period": "нормализованная форма: 'last_N_months:N' или 'range:YYYY-MM-DD:YYYY-MM-DD'",
  "product_words": ["список слов/фраз потребляемой продукции"],
  "regions": ["список регионов"],
  "okved_list": ["список кодов ОКВЭД"],
  "exclusions": ["список ИНН для исключения"],
  "revenue_min": число или null,
  "revenue_max": число или null,
  "trans_sum_min": число или null,
  "trans_cnt_min": число или null
}

Правила нормализации analysis_period:
- "6 месяцев до даты запроса" → "last_N_months:6"
- "квартал до даты запроса" → "last_N_months:3"
- "год до даты запроса" → "last_N_months:12"
- "с 01.01.2025 по 31.12.2025" → "range:2025-01-01:2025-12-31"
- Если не указан — "last_N_months:6"

Если поле не найдено — используй null для чисел, [] для списков."""


class BriefExtractionError(Exception):
    pass


def extract_brief(excel_text: str, client: Any) -> BriefData:
    """
    Call DeepSeek to extract BriefData fields from Excel text.
    Raises BriefExtractionError if required fields are missing or response is invalid.
    """
    logger.info(f"[extract_brief] Starting API call to DeepSeek")
    logger.info(f"[extract_brief] Input text length: {len(excel_text)} chars")
    logger.info(f"[extract_brief] System prompt length: {len(SYSTEM_PROMPT)} chars")
    logger.info(f"[extract_brief] API endpoint: https://api.deepseek.com")
    logger.info(f"[extract_brief] Model: deepseek-chat")
    logger.info(f"[extract_brief] Request timeout: 60 seconds")

    start_time = time.time()
    try:
        logger.debug(f"[extract_brief] Building request payload...")
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": excel_text},
        ]
        logger.debug(f"[extract_brief] Payload ready, connecting to API...")
        logger.info(f"[extract_brief] Sending request to API (will wait max 60s)...")

        message = client.chat.completions.create(
            model="deepseek-chat",
            max_tokens=2048,
            timeout=60,
            messages=messages,
        )
        elapsed = time.time() - start_time
        logger.info(f"[extract_brief] ✓ API response received in {elapsed:.2f}s")
        logger.debug(f"[extract_brief] Response choices: {len(message.choices)}")
    except TimeoutError as e:
        elapsed = time.time() - start_time
        logger.error(f"[extract_brief] ✗ API request TIMEOUT after {elapsed:.2f}s (max was 60s)")
        logger.error(f"[extract_brief] This usually means the API is not responding or network is too slow")
        raise BriefExtractionError(f"DeepSeek API timeout (60s exceeded): {e}")
    except ConnectionError as e:
        elapsed = time.time() - start_time
        logger.error(f"[extract_brief] ✗ CONNECTION ERROR after {elapsed:.2f}s: {e}")
        logger.error(f"[extract_brief] Check: 1) Internet connection, 2) API endpoint reachability, 3) Firewall/proxy")
        raise BriefExtractionError(f"DeepSeek API connection failed: {e}")
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[extract_brief] ✗ API call failed after {elapsed:.2f}s: {type(e).__name__}")
        logger.error(f"[extract_brief] Error: {e}")
        raise BriefExtractionError(f"DeepSeek API call failed: {e}")

    raw = message.choices[0].message.content.strip()
    logger.info(f"[extract_brief] Raw response length: {len(raw)} chars")
    logger.debug(f"[extract_brief] Raw response preview: {raw[:100]}...")

    # Strip markdown code fences if present
    if raw.startswith("```"):
        logger.debug(f"[extract_brief] Detected markdown code fence, stripping...")
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
        logger.debug(f"[extract_brief] After stripping: {len(raw)} chars")

    try:
        data = json.loads(raw)
        logger.info(f"[extract_brief] JSON parsed successfully")
        logger.debug(f"[extract_brief] Keys in response: {list(data.keys())}")
    except json.JSONDecodeError as e:
        logger.error(f"[extract_brief] JSON parsing failed: {e}")
        logger.debug(f"[extract_brief] Raw content preview: {raw[:200]}")
        raise BriefExtractionError(f"DeepSeek returned invalid JSON: {e}\nRaw: {raw[:200]}")

    # Validate required fields
    for required in ("name", "inn_client", "analysis_period"):
        if not data.get(required):
            raise BriefExtractionError(
                f"Required field '{required}' is missing or empty in Claude's response."
            )

    # Normalize regions: if "РФ" or similar, clear the list (means all regions)
    regions = data.get("regions") or []
    logger.info(f"[extract_brief] Raw regions from API: {regions}")
    if regions:
        # Check for "all Russia" indicators (case-insensitive)
        all_russia_indicators = {
            "рф", "россия", "российская федерация",
            "all", "все", "russia", "russian federation"
        }
        regions_lower = [r.lower().strip() for r in regions]
        if any(indicator in regions_lower for indicator in all_russia_indicators):
            logger.info(f"[extract_brief] ⚠️ Detected 'all regions' indicator: {regions}")
            logger.info(f"[extract_brief] Clearing regions list (empty = all regions, no filter)")
            regions = []
    logger.info(f"[extract_brief] Normalized regions: {regions}")

    return BriefData(
        name=data["name"],
        inn_client=[str(i) for i in data["inn_client"]],
        analysis_period=data["analysis_period"],
        product_words=data.get("product_words") or [],
        regions=regions,
        okved_list=data.get("okved_list") or [],
        exclusions=data.get("exclusions") or [],
        revenue_min=int(data["revenue_min"]) if data.get("revenue_min") else 100_000_000,
        revenue_max=int(data["revenue_max"]) if data.get("revenue_max") else None,
        trans_sum_min=int(data["trans_sum_min"]) if data.get("trans_sum_min") else 10_000_000,
        trans_cnt_min=int(data["trans_cnt_min"]) if data.get("trans_cnt_min") else 3,
    )
