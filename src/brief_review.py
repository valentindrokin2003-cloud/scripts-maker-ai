import re

from src.brief_source import (
    EXCLUSION_INN_MARKERS,
    company_names_match,
    extract_client_inns_from_excel_text,
    extract_client_names_from_excel_text,
    is_valid_inn,
)
from src.models import BriefData, BriefIssue, BriefReview
from src.okved_resolver import (
    has_okved_stop_signal,
    has_okved_target_context,
    is_okved_code_too_broad,
)

GENERIC_PRODUCT_WORDS = {
    "продукция",
    "товар",
    "товары",
    "товарная продукция",
    "сырье",
    "материалы",
    "оборудование",
    "комплектующие",
    "запчасти",
    "номенклатура",
}

PERIOD_HINT_PATTERNS = (
    re.compile(r"\b\d+\s*(?:мес(?:яц(?:ев|а)?)?|квартал(?:а|ов)?|год(?:а|ов)?|лет)\b", re.IGNORECASE),
    re.compile(r"\bс\s*\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\s*по\s*\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b", re.IGNORECASE),
    re.compile(r"\bза\s+\d{4}\s+год\b", re.IGNORECASE),
)


def _humanize_period(value: str) -> str:
    if value.startswith("last_N_months:"):
        months = value.split(":", 1)[1]
        return f"Последние {months} мес."
    if value.startswith("range:"):
        _, start_date, end_date = value.split(":", 2)
        return f"{start_date} -> {end_date}"
    return value


def _extract_inn_mentions(excel_text: str) -> list[str]:
    found: list[str] = []
    for line in excel_text.splitlines():
        normalized = line.casefold()
        if "инн" not in normalized:
            continue
        if any(marker in normalized for marker in EXCLUSION_INN_MARKERS):
            continue
        found.extend(re.findall(r"(?<!\d)\d{10,12}(?!\d)", line))
    return list(dict.fromkeys(found))


def _has_explicit_period_hint(excel_text: str) -> bool:
    return any(pattern.search(excel_text) for pattern in PERIOD_HINT_PATTERNS)


def _generic_product_words(words: list[str]) -> list[str]:
    generic: list[str] = []
    for word in words:
        cleaned = re.sub(r"\s+", " ", word.casefold()).strip()
        if cleaned in GENERIC_PRODUCT_WORDS:
            generic.append(word)
    return generic


def _okved_review_issues(excel_text: str, brief: BriefData) -> list[BriefIssue]:
    issues: list[BriefIssue] = []
    if has_okved_stop_signal(excel_text):
        if brief.okved_list:
            issues.append(
                BriefIssue(
                    severity="recommendation",
                    field_name="okved_list",
                    title="ОКВЭД-фильтр противоречит формулировке брифа",
                    detail=(
                        "В тексте есть указание на отсутствие отраслевого ограничения, "
                        f"но сервис все равно выделил коды ОКВЭД: {', '.join(brief.okved_list)}."
                    ),
                )
            )
        return issues

    has_target_context = has_okved_target_context(excel_text)
    if has_target_context and not brief.okved_list:
        issues.append(
            BriefIssue(
                severity="recommendation",
                field_name="okved_list",
                title="Не удалось уверенно определить ОКВЭД-фильтр",
                detail=(
                    "В брифе есть указание на отрасль, тип клиентов или ОКВЭД, "
                    "но сервис не смог подобрать коды из справочника. "
                    "Лучше явно перечислить нужные отрасли или коды."
                ),
            )
        )
        return issues

    broad_codes = [code for code in brief.okved_list if is_okved_code_too_broad(code)]
    if broad_codes:
        issues.append(
            BriefIssue(
                severity="recommendation",
                field_name="okved_list",
                title="ОКВЭД-фильтр получился слишком широким",
                detail=(
                    "Сервис выделил очень общие коды ОКВЭД: "
                    f"{', '.join(broad_codes)}. Лучше уточнить отрасли до более конкретного уровня."
                ),
            )
        )

    if len(brief.okved_list) >= 6:
        issues.append(
            BriefIssue(
                severity="recommendation",
                field_name="okved_list",
                title="Слишком много кодов ОКВЭД в фильтре",
                detail=(
                    f"Сервис выделил {len(brief.okved_list)} кодов ОКВЭД. "
                    "Стоит проверить, не стал ли отраслевой фильтр слишком широким."
                ),
            )
        )

    return issues


def review_brief(excel_text: str, brief: BriefData) -> BriefReview:
    issues: list[BriefIssue] = []

    explicit_names = extract_client_names_from_excel_text(excel_text)
    explicit_inn_mentions = extract_client_inns_from_excel_text(excel_text)
    inn_mentions = explicit_inn_mentions or _extract_inn_mentions(excel_text)

    if len(explicit_names) > 1:
        issues.append(
            BriefIssue(
                severity="critical",
                field_name="name",
                title="В брифе встречаются разные названия заказчика",
                detail=(
                    "Сервис нашел несколько вариантов названия заказчика в явных полях брифа: "
                    f"{', '.join(explicit_names)}."
                ),
            )
        )
    elif explicit_names and not company_names_match(brief.name, explicit_names[0]):
        issues.append(
            BriefIssue(
                severity="critical",
                field_name="name",
                title="Название заказчика определено неверно",
                detail=(
                    "Сервис выделил название заказчика как "
                    f"'{brief.name}', но в брифе указано '{explicit_names[0]}'."
                ),
            )
        )

    if len(brief.inn_client) != 1:
        issues.append(
            BriefIssue(
                severity="critical",
                field_name="inn_client",
                title="Нужен один ИНН заказчика",
                detail=(
                    "Сервис ожидает один ИНН заказчика, но в брифе выделено "
                    f"{len(brief.inn_client)} значений: {', '.join(brief.inn_client)}."
                ),
            )
        )
    elif not is_valid_inn(brief.inn_client[0]):
        issues.append(
            BriefIssue(
                severity="recommendation",
                field_name="inn_client",
                title="ИНН заказчика выглядит некорректным",
                detail=(
                    f"Сервис выделил ИНН {brief.inn_client[0]}, но он не проходит базовую проверку "
                    "формата и контрольных цифр. Лучше перепроверить ИНН вручную."
                ),
            )
        )
    elif explicit_inn_mentions and brief.inn_client[0] not in explicit_inn_mentions:
        issues.append(
            BriefIssue(
                severity="critical",
                field_name="inn_client",
                title="ИНН заказчика определен неверно",
                detail=(
                    "Сервис выделил ИНН заказчика как "
                    f"{brief.inn_client[0]}, но в явном поле брифа указано: "
                    f"{', '.join(explicit_inn_mentions)}."
                ),
            )
        )
    elif len(inn_mentions) > 1:
        issues.append(
            BriefIssue(
                severity="critical",
                field_name="inn_client",
                title="В брифе встречаются разные ИНН",
                detail=(
                    "В строках с ИНН найдено несколько значений. "
                    f"Нужно оставить один ИНН заказчика: {', '.join(inn_mentions)}."
                ),
            )
        )

    if not brief.product_words:
        issues.append(
            BriefIssue(
                severity="critical",
                field_name="product_words",
                title="Не удалось уверенно понять товарную часть",
                detail=(
                    "В брифе нет достаточно явного списка продукции или услуг. "
                    "Добавьте короткий перечень товарных позиций, по которым нужно искать клиентов."
                ),
            )
        )

    generic_words = _generic_product_words(brief.product_words)
    if generic_words:
        issues.append(
            BriefIssue(
                severity="recommendation",
                field_name="product_words",
                title="Товарные формулировки слишком общие",
                detail=(
                    "Сервис выделил слишком широкие слова: "
                    f"{', '.join(generic_words)}. Лучше указать конкретные позиции или группы товаров."
                ),
            )
        )

    if brief.analysis_period == "last_N_months:6" and not _has_explicit_period_hint(excel_text):
        issues.append(
            BriefIssue(
                severity="warning",
                field_name="analysis_period",
                title="Период анализа не указан явно",
                detail=(
                    "Сервис не нашел в брифе явный период и подставил стандартные 6 месяцев. "
                    "Лучше указать точный диапазон или желаемую длительность анализа."
                ),
            )
        )

    if brief.revenue_max is not None and brief.revenue_max < brief.revenue_min:
        issues.append(
            BriefIssue(
                severity="critical",
                field_name="revenue",
                title="Финансовый диапазон противоречив",
                detail=(
                    f"Максимальная выручка ({brief.revenue_max}) меньше минимальной ({brief.revenue_min}). "
                    "Нужно скорректировать ограничения."
                ),
            )
        )

    if not brief.regions and not brief.f_ocrygs:
        issues.append(
            BriefIssue(
                severity="recommendation",
                field_name="regions",
                title="Регион поиска не указан",
                detail=(
                    "Сервис может работать и без региона, но точность подбора будет выше, "
                    "если явно указать целевой регион или список регионов."
                ),
            )
        )

    issues.extend(_okved_review_issues(excel_text, brief))

    status = "needs_revision" if any(issue.severity in {"critical", "warning"} for issue in issues) else "ok"
    return BriefReview(
        status=status,
        issues=issues,
        extracted_fields={
            "client_name": brief.name,
            "inn_client": brief.inn_client,
            "analysis_period": _humanize_period(brief.analysis_period),
            "product_words": brief.product_words,
            "regions": brief.regions,
            "f_ocrygs": brief.f_ocrygs,
            "okved_list": brief.okved_list,
            "okved_explanations": brief.okved_explanations,
            "exclusions": brief.exclusions,
        },
    )
