import json
from typing import Any
from src.models import BriefData

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
    message = client.chat.completions.create(
        model="deepseek-chat",
        max_tokens=2048,
        system_prompt=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": excel_text}],
    )

    raw = message.choices[0].message.content.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise BriefExtractionError(f"Claude returned invalid JSON: {e}\nRaw: {raw[:200]}")

    # Validate required fields
    for required in ("name", "inn_client", "analysis_period"):
        if not data.get(required):
            raise BriefExtractionError(
                f"Required field '{required}' is missing or empty in Claude's response."
            )

    return BriefData(
        name=data["name"],
        inn_client=[str(i) for i in data["inn_client"]],
        analysis_period=data["analysis_period"],
        product_words=data.get("product_words") or [],
        regions=data.get("regions") or [],
        okved_list=data.get("okved_list") or [],
        exclusions=data.get("exclusions") or [],
        revenue_min=int(data["revenue_min"]) if data.get("revenue_min") else 100_000_000,
        revenue_max=int(data["revenue_max"]) if data.get("revenue_max") else None,
        trans_sum_min=int(data["trans_sum_min"]) if data.get("trans_sum_min") else 10_000_000,
        trans_cnt_min=int(data["trans_cnt_min"]) if data.get("trans_cnt_min") else 3,
    )
