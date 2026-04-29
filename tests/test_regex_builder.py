import re

from src.brief_extractor import _extract_product_words_from_excel_text
from src.excel_parser import parse_excel_to_text
from src.regex_builder import build_local_regex, validate_regex_patterns


def _matches(patterns, text):
    return any(re.search(pattern, text) for pattern in patterns)


def _build_from_real_brief(path):
    excel_text = parse_excel_to_text(path)
    product_words = _extract_product_words_from_excel_text(excel_text)
    return build_local_regex(product_words)


def test_tire_patterns_from_regexp_examples():
    patterns = build_local_regex(
        [
            "строительные шины",
            "шины для эскаватора",
            "шины для погрузчика",
        ]
    )

    assert _matches(patterns, "оплата шины для экскаватора")
    assert _matches(patterns, "строительные шины")
    assert _matches(patterns, "погрузчик шины")


def test_box_patterns_from_regexp_examples():
    patterns = build_local_regex(
        [
            "Коробка самосборная из картона",
            "коробка с логотипом",
            "картонная упаковка",
            "коробка крышка-дно",
        ]
    )

    assert _matches(patterns, "коробка с логотипом")
    assert _matches(patterns, "картонная упаковка")
    assert _matches(patterns, "коробка крышка дно")


def test_cleaning_patterns_from_regexp_examples():
    patterns = build_local_regex(
        [
            "моющее средство для посудомоечных машин Ecolab",
            "антинакипин",
            "антиржавчина",
            "дезинфицирующее средство",
            "кислотное средство",
        ]
    )

    assert _matches(patterns, "ecolab")
    assert _matches(patterns, "анти накипь")
    assert _matches(patterns, "дезинфицирующее средство")
    assert _matches(patterns, "средство кислотное")
    assert not any("посудомоеч" in pattern or "машин" in pattern for pattern in patterns)


def test_flooring_patterns_from_regexp_examples():
    patterns = build_local_regex(
        [
            "напольное покрытие",
            "ленолеум",
            "покрытие для спортзала",
            "автолин",
            "транслин",
        ]
    )

    assert _matches(patterns, "линолеум")
    assert _matches(patterns, "ленолеум")
    assert _matches(patterns, "покрытие для спортзала")
    assert _matches(patterns, "автолин")


def test_metal_patterns_from_regexp_examples():
    patterns = build_local_regex(
        ["Металлоконструкция", "Каркасы", "Листы", "Трубы", "балки", "Сетка", "Швеллер"]
    )

    assert _matches(patterns, "металлоконструкция")
    assert _matches(patterns, "каркасы")
    assert _matches(patterns, "трубы")
    assert _matches(patterns, "швеллер")


def test_washing_patterns_from_regexp_examples():
    patterns = build_local_regex(
        [
            "капсулы для стирки",
            "стиральные порошки",
            "жидкость для мытья посуды",
        ]
    )

    assert _matches(patterns, "капсулы для стирки")
    assert _matches(patterns, "стиральный порошок")
    assert _matches(patterns, "жидкость для мытья посуды")


def test_precious_scrap_patterns_from_regexp_examples():
    patterns = build_local_regex(
        [
            "лом и отходы, содержащие драгоценные металлы",
            "за ЛОДМ",
            "За ДМ в ломах",
        ]
    )

    assert _matches(patterns, "за лодм")
    assert _matches(patterns, "за дм в ломах")
    assert _matches(patterns, "лом содержащий драг металлы")


def test_food_patterns_from_regexp_examples():
    patterns = build_local_regex(
        [
            "Импортные кондитерские изделия",
            "российская овощная консервация",
        ]
    )

    assert _matches(patterns, "кондитерские изделия")
    assert _matches(patterns, "изделия кондитерские")
    assert _matches(patterns, "овощи консервированные")
    assert not any("импортн" in pattern or "российск" in pattern for pattern in patterns)


def test_decor_lighting_patterns_from_regexp_examples():
    patterns = build_local_regex(
        [
            "светодиодные консоли",
            "панель кронштейн день победы",
            "украшения дорожных столбов",
            "каркасная иллюминация",
            "светодиодные фигуры",
        ]
    )

    assert _matches(patterns, "светодиодные консоли")
    assert _matches(patterns, "панель кронштейн день победы")
    assert _matches(patterns, "украшение дорожных столбов")
    assert _matches(patterns, "каркасная иллюминация")
    assert _matches(patterns, "светодиодная фигура")


def test_interactive_display_patterns_from_regexp_examples():
    patterns = build_local_regex(
        [
            "встраиваемые сенсорные интерактивные мониторы",
            "встраиваемые сенсорные интерактивные панели",
        ]
    )

    assert _matches(patterns, "сенсорный монитор")
    assert _matches(patterns, "панель интерактивная")
    assert _matches(patterns, "встраиваемая панель")


def test_auto_parts_patterns_from_regexp_examples():
    patterns = build_local_regex(
        [
            "запчасти для камаз",
            "сальник для грузового автомобиля",
            "ремкомплект для маз",
        ]
    )

    assert _matches(patterns, "запчасти для камаз")
    assert _matches(patterns, "грузовой автомобиль сальник")
    assert _matches(patterns, "ремкомплект маз")


def test_validate_regex_normalizes_short_quantifier_syntax():
    assert validate_regex_patterns([r"\bтест\w{,3}\b"]) == [r"\bтест\w{0,3}\b"]


def test_bzs_excel_phrases_do_not_create_broad_dependent_patterns():
    patterns = build_local_regex(
        [
            "коннекторы для обогрева",
            "гермовводы",
            "герметичные соединения проводов",
            "коннекторы светильников",
            "уголок для сборки стеклопакетов с проводным соединением",
            "вольфрамовая нить",
            "медная луженая шинка (шина)",
            "промышленые разъемы",
        ]
    )

    assert _matches(patterns, "герметичное соединение проводов")
    assert _matches(patterns, "медная луженая шинка")
    assert _matches(patterns, "промышленные разъемы")
    assert not any(pattern == r"\bшин\w{0,1}\b" for pattern in patterns)
    assert not any("медн" in pattern and "шина" in pattern for pattern in patterns)
    assert not any("герметичн" in pattern and "провод" in pattern for pattern in patterns)


def test_bam_real_brief_keeps_multiline_protein_products():
    patterns = _build_from_real_brief("data/ТЗ_BAM.xlsx")

    assert _matches(patterns, "растительные протеиновые напитки")
    assert _matches(patterns, "протеиновый порошок")
    assert _matches(patterns, "shock milk protein")


def test_rufas_real_brief_builds_facade_panel_patterns():
    patterns = _build_from_real_brief("data/ТЗ_Rufas.xlsx")

    assert _matches(patterns, "фасадные кассеты")
    assert _matches(patterns, "алюминиевая панель")
    assert _matches(patterns, "потолочные панели")


def test_leodata_real_brief_builds_miner_and_server_patterns():
    patterns = _build_from_real_brief("data/ТЗ_Leodata.xlsx")

    assert _matches(patterns, "asic майнер")
    assert _matches(patterns, "whatsminer")
    assert _matches(patterns, "вычислительное серверное оборудование")


def test_transservis_real_brief_does_not_trigger_precious_scrap_patterns():
    patterns = _build_from_real_brief("data/ТЗ_Transservis.xlsx")

    assert _matches(patterns, "модульные здания")
    assert _matches(patterns, "вахтовый поселок")
    assert _matches(patterns, "строительные бытовки и контейнерные здания")
    assert not any("лодм" in pattern or "драг" in pattern for pattern in patterns)
