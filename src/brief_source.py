import re


EXCLUSION_INN_MARKERS = (
    "исключ",
    "стоп-лист",
    "стоп лист",
)


def _normalize_label(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip(" :")


def _clean_value(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).strip(" \"'«»")


def _iter_labeled_rows(excel_text: str):
    for line in excel_text.splitlines():
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 2:
            continue
        label = _normalize_label(parts[0])
        value = _clean_value(" | ".join(part for part in parts[1:] if part.strip()))
        if value:
            yield label, value


def _is_client_name_label(label: str) -> bool:
    if ("назв" in label or "наименован" in label) and (
        "заказ" in label or "клиент" in label
    ):
        return True
    return label in {"заказчик", "клиент"}


def _is_client_inn_label(label: str) -> bool:
    if "инн" not in label:
        return False
    if any(marker in label for marker in EXCLUSION_INN_MARKERS):
        return False
    return "заказ" in label or "клиент" in label or label == "инн"


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def extract_client_names_from_excel_text(excel_text: str) -> list[str]:
    names = [
        value
        for label, value in _iter_labeled_rows(excel_text)
        if _is_client_name_label(label)
    ]
    return _dedupe(names)


def extract_client_inns_from_excel_text(excel_text: str) -> list[str]:
    inns: list[str] = []
    for label, value in _iter_labeled_rows(excel_text):
        if not _is_client_inn_label(label):
            continue
        inns.extend(re.findall(r"(?<!\d)\d{10,12}(?!\d)", value))
    return _dedupe(inns)


def canonicalize_company_name(name: str) -> str:
    legal_forms = (
        "ооо",
        "ао",
        "пао",
        "оао",
        "зао",
        "ип",
        "нко",
        "пко",
        "пт",
    )
    value = name.casefold()
    value = value.replace("«", " ").replace("»", " ")
    value = value.replace('"', " ").replace("'", " ")
    value = re.sub(rf"\b({'|'.join(legal_forms)})\b", " ", value)
    return re.sub(r"[^a-zа-я0-9]+", "", value)


def company_names_match(left: str, right: str) -> bool:
    left_normalized = canonicalize_company_name(left)
    right_normalized = canonicalize_company_name(right)
    if not left_normalized or not right_normalized:
        return False
    if left_normalized == right_normalized:
        return True
    short_name, long_name = sorted(
        (left_normalized, right_normalized),
        key=len,
    )
    return len(short_name) >= 6 and short_name in long_name


def is_valid_inn(inn: str) -> bool:
    if not re.fullmatch(r"\d{10}|\d{12}", inn):
        return False
    if len(set(inn)) == 1:
        return False

    digits = [int(char) for char in inn]
    if len(digits) == 10:
        checksum = (
            2 * digits[0]
            + 4 * digits[1]
            + 10 * digits[2]
            + 3 * digits[3]
            + 5 * digits[4]
            + 9 * digits[5]
            + 4 * digits[6]
            + 6 * digits[7]
            + 8 * digits[8]
        ) % 11 % 10
        return checksum == digits[9]

    checksum_11 = (
        7 * digits[0]
        + 2 * digits[1]
        + 4 * digits[2]
        + 10 * digits[3]
        + 3 * digits[4]
        + 5 * digits[5]
        + 9 * digits[6]
        + 4 * digits[7]
        + 6 * digits[8]
        + 8 * digits[9]
    ) % 11 % 10
    checksum_12 = (
        3 * digits[0]
        + 7 * digits[1]
        + 2 * digits[2]
        + 4 * digits[3]
        + 10 * digits[4]
        + 3 * digits[5]
        + 5 * digits[6]
        + 9 * digits[7]
        + 4 * digits[8]
        + 6 * digits[9]
        + 8 * digits[10]
    ) % 11 % 10
    return checksum_11 == digits[10] and checksum_12 == digits[11]
