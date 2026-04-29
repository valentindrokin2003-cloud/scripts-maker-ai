import logging
import re
import time
from typing import Any

from src.brief_source import (
    extract_client_inns_from_excel_text,
    extract_client_names_from_excel_text,
)
from src.llm_json import LLMJsonError, parse_llm_json, strip_markdown_json
from src.models import BriefData
from src.okved_resolver import resolve_okved_resolution
from src.region_normalizer import resolve_region_filters
from src.settings import DEFAULT_LLM_MODEL

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

Правила извлечения product_words:
- Извлекай именно поставляемые/потребляемые товарные позиции, а не все существительные из описания.
- Сохраняй короткие исходные фразы, достаточные для дальнейшего сопоставления со словарем.
- Не выделяй зависимые объекты и назначение как отдельные товары: в "коннекторы светильников" товар — "коннекторы", не "светильники"; в "уголок для сборки стеклопакетов с проводным соединением" товар — "уголок", не "стеклопакет" и не "провод".
- Не превращай материал или уточнение в отдельный товар: "вольфрамовая нить" не равно бытовая "нить"; "медная луженая шинка" не равно "мед".
- Если фраза описывает разновидность товара, оставляй главный товарный термин: "промышленные разъемы" → "разъемы".

Если поле не найдено — используй null для чисел, [] для списков."""


class BriefExtractionError(Exception):
    pass


def _extract_product_words_from_excel_text(excel_text: str) -> list[str]:
    lines = excel_text.splitlines()
    for index, line in enumerate(lines):
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 2:
            continue
        if parts[0].casefold() != "потребляемая продукция":
            continue
        value_lines = [parts[1]]
        for next_line in lines[index + 1 :]:
            stripped = next_line.strip()
            if not stripped:
                break
            if stripped.casefold() == "поставляемая продукция":
                break
            if stripped.startswith("===") or "|" in stripped:
                break
            value_lines.append(stripped)
        return _split_product_phrases("\n".join(value_lines))
    return []


def _split_product_phrases(value: str) -> list[str]:
    phrases = []
    current = []
    depth = 0
    for char in value:
        if char == "(":
            depth += 1
        elif char == ")" and depth:
            depth -= 1

        if char in ",;\n" and depth == 0:
            phrase = "".join(current).strip()
            if phrase:
                phrases.append(phrase)
            current = []
            continue
        current.append(char)

    phrase = "".join(current).strip()
    if phrase:
        phrases.append(phrase)
    return phrases


def extract_brief(excel_text: str, client: Any, model: str = DEFAULT_LLM_MODEL) -> BriefData:
    """
    Call DeepSeek to extract BriefData fields from Excel text.
    Raises BriefExtractionError if required fields are missing or response is invalid.
    """
    logger.info(f"[extract_brief] Starting API call to DeepSeek")
    logger.info(f"[extract_brief] Input text length: {len(excel_text)} chars")
    logger.info(f"[extract_brief] System prompt length: {len(SYSTEM_PROMPT)} chars")
    logger.info(f"[extract_brief] API endpoint: https://api.deepseek.com")
    logger.info(f"[extract_brief] Model: {model}")
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
            model=model,
            max_tokens=8192,
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

    try:
        data = parse_llm_json(raw)
        logger.info(f"[extract_brief] JSON parsed successfully")
        logger.debug(f"[extract_brief] Keys in response: {list(data.keys())}")
    except LLMJsonError as e:
        stripped = strip_markdown_json(raw)
        logger.error(f"[extract_brief] JSON parsing failed: {e}")
        logger.debug(f"[extract_brief] Raw content preview: {stripped[:200]}")
        # Check if response appears truncated
        if not stripped.rstrip().endswith('}') and len(stripped) > 100:
            logger.error(f"[extract_brief] ⚠️ Response appears truncated (doesn't end with closing brace)")
            logger.error(f"[extract_brief] Possible solution: Increase max_tokens in API call")
            logger.debug(f"[extract_brief] Last 100 chars: ...{stripped[-100:]}")
        raise BriefExtractionError(f"DeepSeek returned invalid JSON: {e}\nRaw: {stripped[:200]}")

    explicit_names = extract_client_names_from_excel_text(excel_text)
    explicit_inns = extract_client_inns_from_excel_text(excel_text)
    resolved_name = explicit_names[0] if explicit_names else data.get("name")
    resolved_inn_client = explicit_inns if explicit_inns else data.get("inn_client")

    # Validate required fields after overlaying explicit Excel values.
    for required, value in (
        ("name", resolved_name),
        ("inn_client", resolved_inn_client),
        ("analysis_period", data.get("analysis_period")),
    ):
        if not value:
            raise BriefExtractionError(
                f"Required field '{required}' is missing or empty in resolved brief data."
            )

    raw_regions = data.get("regions") or []
    logger.info(f"[extract_brief] Raw regions from API: {raw_regions}")
    region_filters = resolve_region_filters(raw_regions)
    logger.info(
        "[extract_brief] Normalized region filters: regions=%s, f_ocrygs=%s",
        region_filters.regions,
        region_filters.f_ocrygs,
    )
    product_words = _extract_product_words_from_excel_text(excel_text)
    if product_words:
        logger.info(
            "[extract_brief] Product words extracted from Excel row: "
            f"{product_words}"
        )
    else:
        product_words = data.get("product_words") or []

    okved_resolution = resolve_okved_resolution(
        excel_text,
        data.get("okved_list") or [],
        client=client,
        model=model,
    )
    logger.info("[extract_brief] Resolved OKVED list: %s", okved_resolution.codes)
    logger.info("[extract_brief] OKVED decision reason: %s", okved_resolution.decision_reason)

    return BriefData(
        name=resolved_name,
        inn_client=[str(i).strip() for i in resolved_inn_client],
        analysis_period=data["analysis_period"],
        product_words=product_words,
        regions=region_filters.regions,
        f_ocrygs=region_filters.f_ocrygs,
        okved_list=okved_resolution.codes,
        okved_explanations=okved_resolution.explanations,
        exclusions=data.get("exclusions") or [],
        revenue_min=int(data["revenue_min"]) if data.get("revenue_min") else 100_000_000,
        revenue_max=int(data["revenue_max"]) if data.get("revenue_max") else None,
        trans_sum_min=int(data["trans_sum_min"]) if data.get("trans_sum_min") else 10_000_000,
        trans_cnt_min=int(data["trans_cnt_min"]) if data.get("trans_cnt_min") else 3,
    )
