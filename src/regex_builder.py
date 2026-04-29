import re
from collections.abc import Iterable


SEPARATOR = r"[-/ ]*"
OPTIONAL_CONNECTOR = r"(?:(?:для|к|на|с|из|от|в|по|за|основе)[-/ ]*)?"

TOKEN_RE = re.compile(r"[a-zа-я0-9]+", re.IGNORECASE)

ENDINGS = (
    "иями",
    "ями",
    "ами",
    "ого",
    "его",
    "ому",
    "ему",
    "ыми",
    "ими",
    "ых",
    "их",
    "ой",
    "ый",
    "ий",
    "ая",
    "яя",
    "ое",
    "ее",
    "ые",
    "ие",
    "ов",
    "ев",
    "ей",
    "ам",
    "ям",
    "ах",
    "ях",
    "ом",
    "ем",
    "а",
    "я",
    "ы",
    "и",
    "е",
    "у",
    "ю",
)

STOPWORDS = {
    "в",
    "для",
    "из",
    "и",
    "или",
    "к",
    "кроме",
    "на",
    "основе",
    "от",
    "по",
    "с",
    "со",
}

TAIL_CONTEXT_STOPWORDS = {
    "обогрев",
    "провод",
    "проводной",
    "светильник",
    "соединение",
    "стеклопакет",
}

TAIL_CONTEXT_STEMS = {
    "провод",
    "светильник",
    "стеклопакет",
}

ADJECTIVE_ENDINGS = (
    "ая",
    "яя",
    "ое",
    "ее",
    "ые",
    "ие",
    "ый",
    "ий",
    "ой",
    "ого",
    "его",
    "ому",
    "ему",
    "ыми",
    "ими",
    "ых",
    "их",
)

MANUAL_STEMS = {
    "антинакипин": "накип",
    "антиржавчина": "ржавчин",
    "антизасор": "засор",
    "балки": "бало?к",
    "балка": "бало?к",
    "дезинфицирующее": r"дез[иы]нф[еи]цир",
    "дезинфицирующий": r"дез[иы]нф[еи]цир",
    "дезинфицирующееся": r"дез[иы]нф[еи]цир",
    "иллюминация": r"илл?юминац",
    "ленолеум": r"л[ие]нол[еи]ум",
    "линолеум": r"л[ие]нол[еи]ум",
    "металлоконструкция": r"метал\w*[-/ ]*конструк[тц]",
    "металлоконструкции": r"метал\w*[-/ ]*конструк[тц]",
    "панель": r"панн?ел",
    "панели": r"панн?ел",
    "поселки": r"посело?к",
    "поселок": r"посело?к",
    "погрузчика": r"погрузо?ч",
    "погрузчик": r"погрузо?ч",
    "порошки": r"порошо?к",
    "порошок": r"порошо?к",
    "разъём": r"разъ[её]м",
    "разъёмы": r"разъ[её]м",
    "разъем": r"разъ?[её]м",
    "разъемы": r"разъ?[её]м",
    "средства": "средств",
    "средство": "средств",
    "стеклоочиститель": r"стекло[-/ ]*очистит",
    "шинка": "шинк",
    "шинки": "шинк",
    "швеллер": r"швелл?ер",
    "швеллеры": r"швелл?ер",
}


def _normalise(value: str) -> str:
    return value.casefold().replace("ё", "е")


def _tokens(value: str) -> list[str]:
    return TOKEN_RE.findall(_normalise(value))


def _stem(token: str) -> str:
    if token in MANUAL_STEMS:
        return MANUAL_STEMS[token]
    if token.endswith("ъем"):
        return r"разъ?[её]м"
    for ending in ENDINGS:
        if len(token) - len(ending) >= 4 and token.endswith(ending):
            return token[: -len(ending)].rstrip("ь")
    return token.rstrip("ь")


def _word_pattern(stem: str, suffix: str = r"\w{0,3}") -> str:
    if "\\" in stem or "[" in stem or "?" in stem or "*" in stem:
        return stem + suffix
    return re.escape(stem) + suffix


def _content_stems(phrase: str) -> list[str]:
    stems = []
    phrase = re.sub(r"\([^)]*\)", " ", phrase)
    for token in _tokens(phrase):
        if token in STOPWORDS:
            continue
        stem = _stem(token)
        if stem and stem not in stems:
            stems.append(stem)
    return stems


def _split_phrases(product_words: Iterable[str]) -> list[str]:
    phrases = []
    for value in product_words:
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


def _parenthetical_brand_patterns(phrase: str) -> list[str]:
    patterns = []
    for group in re.findall(r"\(([^)]*)\)", phrase):
        for token in _tokens(group):
            if len(token) >= 4 and re.search(r"[a-z0-9]", token):
                patterns.append(rf"\b{re.escape(token)}\w{{0,3}}\b")
    return patterns


def _phrase_patterns(phrase: str) -> list[str]:
    patterns = _parenthetical_brand_patterns(phrase)
    tokens = [
        token
        for token in _tokens(re.sub(r"\([^)]*\)", " ", phrase))
        if token not in STOPWORDS
    ]
    stems = []
    for token in tokens:
        stem = _stem(token)
        if stem and stem not in stems:
            stems.append(stem)
    if not stems:
        return patterns
    if len(stems) == 1:
        patterns.append(rf"\b{_word_pattern(stems[0])}\b")
        return patterns

    for left, right in zip(stems, stems[1:]):
        left_pattern = _word_pattern(left)
        right_pattern = _word_pattern(right)
        patterns.extend(
            [
                rf"\b{left_pattern}{SEPARATOR}{OPTIONAL_CONNECTOR}{right_pattern}\b",
                rf"\b{right_pattern}{SEPARATOR}{OPTIONAL_CONNECTOR}{left_pattern}\b",
            ]
        )

    tail_index = len(stems) - 1
    tail_token = tokens[-1]
    tail_stem = _stem(tail_token)
    if (
        len(stems) >= 3
        and tokens[0].endswith(ADJECTIVE_ENDINGS)
        and (
            tail_token in TAIL_CONTEXT_STOPWORDS
            or tail_stem in TAIL_CONTEXT_STEMS
        )
    ):
        tail_index = 1

    first = _word_pattern(stems[0])
    last = _word_pattern(stems[tail_index])
    middle = ""
    if tail_index > 1:
        middle = rf"(?:\w+{SEPARATOR}){{0,{tail_index - 1}}}"
    patterns.extend([
        rf"\b{first}{SEPARATOR}{middle}{OPTIONAL_CONNECTOR}{last}\b",
        rf"\b{last}{SEPARATOR}{OPTIONAL_CONNECTOR}{middle}{first}\b",
    ])
    return patterns


def _contains_any(blob: str, values: Iterable[str]) -> bool:
    return any(value in blob for value in values)


def _cleaning_patterns(blob: str) -> list[str]:
    patterns = []
    if "ecolab" in blob or "эколаб" in blob:
        patterns.extend([r"\becolab\b", r"\bэколаб\b"])
    if _contains_any(blob, ("антизасор", "антинакип", "антиржав")):
        patterns.append(r"\bанти[-/ ]*(?:засор|накип|ржавчин)\w{0,3}\b")
    if _contains_any(blob, ("щелоч", "кислот")):
        patterns.extend(
            [
                r"\b(?:щелочн\w{0,3}|кислотн\w{0,3})[-/ ]*средств\w{0,2}\b",
                r"\bсредств\w{0,2}[-/ ]*(?:щелочн\w{0,3}|кислотн\w{0,3})\b",
            ]
        )
    if "стеклоочист" in blob:
        patterns.append(r"\bстекло[-/ ]*очистит\w*\b")
    if "универсальн" in blob and "моющ" in blob:
        patterns.append(r"\bуниверсальн\w{0,3}[-/ ]*моющ\w*\b")
    if "моющ" in blob or "средств" in blob:
        patterns.extend(
            [
                r"\bмоющ\w{0,3}[-/ ]*средств\w{0,2}\b",
                r"\bсредств\w{0,2}[-/ ]*моющ\w{0,3}\b",
            ]
        )
    if "дезинф" in blob or "дезынф" in blob:
        patterns.extend(
            [
                r"\bдез[иы]нф[еи]цир\w*[-/ ]*средств\w{0,2}\b",
                r"\bсредств\w{0,2}[-/ ]*дез[иы]нф[еи]цир\w*\b",
            ]
        )
    return patterns


def _food_patterns(blob: str) -> list[str]:
    patterns = []
    if _contains_any(blob, ("кондитер", "издел")):
        patterns.extend(
            [
                r"\bкондитерск\w{0,2}[-/ ]*издел\w{0,2}\b",
                r"\bиздел\w{0,2}[-/ ]*кондитерск\w{0,2}\b",
            ]
        )
    if _contains_any(blob, ("овощ", "консерв", "огур", "помидор", "томат", "кукуруз", "фасол", "лечо")):
        vegetable = r"(?:овощ\w{0,3}|растител\w*|огуре?ц\w{0,2}|помидор\w{0,2}|томат\w{0,2})"
        preserve = r"(?:консерв\w*|(?:слабо[-/ ]*)?солен\w{0,2}|маринован\w*)"
        specific = r"(?:горо[хш]\w{0,2}|кукуруз\w*|фасол\w*|лечо)"
        process = r"(?:консервир\w*|стерилизован\w*|маринов\w*)"
        patterns.extend(
            [
                rf"\b{vegetable}[-/ ]*{preserve}\b",
                rf"\b{preserve}[-/ ]*{vegetable}\b",
                rf"\b{specific}[-/ ]*(?:зел|сахар|струч|из[-/ ]*перц|из[-/ ]*томат|томат)?\w*[-/ ]*{process}\b",
                rf"\b{process}[-/ ]*{specific}\b",
            ]
        )
    return patterns


def _tire_patterns(blob: str) -> list[str]:
    if "шин" not in blob:
        return []
    modifiers = []
    if "строительн" in blob:
        modifiers.append("строительн")
    if "экскават" in blob or "эскават" in blob:
        modifiers.append("э?к?скават")
    if "погруз" in blob:
        modifiers.append("погрузо?ч")
    if not modifiers:
        return []
    group = "(?:" + "|".join(modifiers) + ")"
    return [
        rf"\bшин\w{{0,1}}[-/ ]*(?:для|на)?[-/ ]*{group}\w*\b",
        rf"\b{group}\w*[-/ ]*шин\w{{0,1}}\b",
    ]


def _decor_lighting_patterns(blob: str) -> list[str]:
    if not _contains_any(blob, ("консол", "кроншт", "иллюминац", "фигур", "столб", "опор")):
        return []
    item = r"(?:консол\w{0,2}|панн?ел\w*[-/ ]*кронд?шт\w*)"
    modifier = (
        r"(?:светодиодн\w*|светов\w*|де?н\w{0,2}[-/ ]*побед\w*|"
        r"9[-/ ]*ма\w{0,1}|звезд\w{0,2}|триколор\w*|флаг\w{0,2}|"
        r"знам\w{0,3}|побед\w{0,2}|столб\w{0,2}|опор\w{0,1})"
    )
    patterns = [
        rf"\b{item}[-/ ]*(?:для|на)?[-/ ]*{modifier}\b",
        rf"\b{modifier}[-/ ]*{item}\b",
    ]
    if "украш" in blob or "столб" in blob or "опор" in blob:
        patterns.append(r"\bукраш\w*[-/ ]*(?:для|на)?[-/ ]*дорож\w*[-/ ]*(?:столб\w*|опор\w*)\b")
    if "иллюминац" in blob:
        patterns.extend(
            [
                r"\b(?:каркасн\w{0,3}|праздничн\w{0,3})[-/ ]*илл?юминац\w{0,2}\b",
                r"\bилл?юминац\w{0,2}[-/ ]*(?:каркасн\w{0,3}|праздничн\w{0,3})\b",
            ]
        )
    if "фигур" in blob:
        patterns.extend(
            [
                r"\bфигур\w{0,2}[-/ ]*(?:светодиод\w*|светов\w{0,2})\b",
                r"\b(?:светодиод\w*|светов\w{0,2})[-/ ]*фигур\w{0,2}\b",
            ]
        )
    return patterns


def _interactive_display_patterns(blob: str) -> list[str]:
    if not _contains_any(blob, ("монитор", "панел", "панель", "интерактив", "сенсор", "встра")):
        return []
    if not _contains_any(blob, ("монитор", "панел", "панель")):
        return []
    if not _contains_any(blob, ("интерактив", "сенсор", "встра", "медицинск")):
        return []
    device = r"(?:монитор\w{0,2}|панн?ел\w{0,2}|терминал\w{0,2})"
    modifier = r"(?:интеракт\w*|сенсорн\w{0,3}|встра[ие]ваем\w{0,3}|медицинск\w{0,3})"
    return [
        rf"\b{modifier}[-/ ]*{device}\b",
        rf"\b{device}[-/ ]*(?:с|для)?[-/ ]*{modifier}\b",
    ]


def _auto_parts_patterns(blob: str) -> list[str]:
    if not _contains_any(blob, ("запчаст", "зап част", "сальник", "патруб", "ремкомпл", "камаз", "грузов")):
        return []
    part = (
        r"(?:зап\w*[-/ ]*част\w{0,3}|част\w{0,3}[-/ ]*зап\w*|"
        r"резин\w*[-/ ]*тех\w*[-/ ]*изд\w*|сальник\w{0,2}|"
        r"патрубо?к\w{0,3}|сис\w*[-/ ]*охл\w*|рем\w*[-/ ]*компл\w*)"
    )
    vehicle = (
        r"(?:камаз\w{0,2}|маз\w{0,1}|газ\w{0,1}|грузов\w{0,3}|"
        r"груз\w*[-/ ]*(?:авто\w*|автомоб\w*|трансп\w*)|авт\w*[-/ ]*груз\w*)"
    )
    return [
        rf"\b{part}[-/ ]*(?:для|к|в|от)?[-/ ]*{vehicle}\b",
        rf"\b{vehicle}[-/ ]*{part}\b",
    ]


def _box_patterns(blob: str) -> list[str]:
    if not _contains_any(blob, ("короб", "упаков")):
        return []
    attrs = (
        r"картон\w*|каширов\w*|логотип\w{0,2}|магнит\w*|клапан\w*|"
        r"крыш\w*[-/ ]*д[он]\w{0,2}|шкатуло?к\w*|самосбор\w*"
    )
    return [
        rf"\b(?:короб\w{{0,2}}|упаков\w{{0,2}})[-/ ]*(?:из|с)?[-/ ]*(?:{attrs})\b",
        rf"\b(?:{attrs})[-/ ]*(?:короб\w{{0,2}}|упаков\w{{0,2}})\b",
    ]


def _flooring_patterns(blob: str) -> list[str]:
    patterns = []
    if _contains_any(blob, ("линолеум", "ленолеум")):
        patterns.append(r"\bл[ие]нол[еи]ум\w{0,2}\b")
    if "покрыт" in blob:
        modifiers = r"(?:напол\w*|сценич\w*|танцевальн\w{0,3}|шоу|спорт\w*[-/ ]*зал\w{0,2}|сцен\w{0,2})"
        patterns.extend(
            [
                rf"\b{modifiers}[-/ ]*покрыт\w{{0,2}}\b",
                rf"\bпокрыт\w{{0,2}}[-/ ]*(?:на|для)?[-/ ]*{modifiers}\b",
            ]
        )
    if "автолин" in blob:
        patterns.append(r"\bавтолин\w{0,2}\b")
    if "транслин" in blob:
        patterns.append(r"\bтранслин\w{0,2}\b")
    return patterns


def _metal_patterns(blob: str) -> list[str]:
    patterns = []
    if "металлоконструк" in blob:
        patterns.extend(
            [
                r"\bметал\w*[-/ ]*конструк[тц]\w{0,3}\b",
                r"\bконструк[тц]\w{0,3}[-/ ]*(?:из[-/ ]*)?метал\w*\b",
            ]
        )
    for key, pattern in (
        ("каркас", r"\bкаркас\w{0,2}\b"),
        ("лист", r"\bлист\w{0,2}\b"),
        ("труб", r"\bтруб\w{0,2}\b"),
        ("балк", r"\bбало?к\w{0,2}\b"),
        ("сетк", r"\bсетк\w{0,1}\b"),
        ("швеллер", r"\bшвелл?ер\w{0,2}\b"),
    ):
        if key in blob:
            patterns.append(pattern)
    return patterns


def _washing_patterns(blob: str) -> list[str]:
    patterns = []
    if "стир" in blob:
        item_group = r"(?:капсул\w{0,2}|гел\w{0,2}|порошо?к\w{0,2})"
        patterns.extend(
            [
                rf"\b{item_group}[-/ ]*(?:для|к)?[-/ ]*стир\w*\b",
                rf"\bстир\w*[-/ ]*{item_group}\b",
            ]
        )
    if "посуд" in blob and ("мыт" in blob or "моющ" in blob):
        item_group = r"(?:жидк\w{0,5}|средств\w{0,2}|порошо?к\w{0,2})"
        patterns.extend(
            [
                rf"\b{item_group}[-/ ]*(?:для|к)?[-/ ]*мыт\w{{0,3}}[-/ ]*посуд\w*\b",
                rf"\bмыт\w{{0,3}}[-/ ]*посуд\w*[-/ ]*{item_group}\b",
            ]
        )
    return patterns


def _precious_scrap_patterns(blob: str) -> list[str]:
    tokens = _tokens(blob)
    if not any(
        token == "лодм"
        or token == "дм"
        or token.startswith("драг")
        or token.startswith("лом")
        or token.startswith("отход")
        for token in tokens
    ):
        return []
    dm = r"(?:дм|драг\w*[-/ ]*мет\w*)"
    scrap = r"(?:лом\w{0,3}|отход\w*)"
    return [
        r"\bза[-/ ]*лодм\b",
        rf"\bза[-/ ]*{dm}[-/ ]*(?:в|из|с)?[-/ ]*лом\w{{0,3}}\b",
        rf"\b{scrap}[-/ ]*(?:содерж\w*|в|из|с)?[-/ ]*{dm}\b",
        rf"\b{dm}[-/ ]*(?:содерж\w*|в|из|с)?[-/ ]*{scrap}\b",
    ]


def build_local_regex(product_words: list[str]) -> list[str]:
    """Build deterministic seed regex patterns from product phrases."""
    phrases = _split_phrases(product_words)
    blob = _normalise(" ".join(phrases))

    patterns = []
    for builder in (
        _food_patterns,
        _cleaning_patterns,
        _tire_patterns,
        _decor_lighting_patterns,
        _interactive_display_patterns,
        _auto_parts_patterns,
        _box_patterns,
        _flooring_patterns,
        _metal_patterns,
        _washing_patterns,
        _precious_scrap_patterns,
    ):
        patterns.extend(builder(blob))

    if not patterns:
        for phrase in phrases:
            patterns.extend(_phrase_patterns(phrase))

    return validate_regex_patterns(patterns)


def validate_regex_patterns(patterns: Iterable[str]) -> list[str]:
    valid = []
    seen = set()
    for pattern in patterns:
        if not isinstance(pattern, str) or not pattern:
            continue
        pattern = pattern.replace(r"\w{,3}", r"\w{0,3}")
        pattern = pattern.replace(r"\w{,2}", r"\w{0,2}")
        pattern = pattern.replace(r"\w{,1}", r"\w{0,1}")
        if pattern in seen:
            continue
        try:
            re.compile(pattern)
        except re.error:
            continue
        seen.add(pattern)
        valid.append(pattern)
    return valid
