from src.brief_review import review_brief
from src.models import BriefData


def test_review_brief_flags_missing_products_and_implicit_period():
    brief = BriefData(
        name="ООО Фреш",
        inn_client=["5009138436"],
        analysis_period="last_N_months:6",
        product_words=[],
    )

    review = review_brief("Название компании заказчика | ООО Фреш\nИНН заказчика | 5009138436", brief)

    assert review.status == "needs_revision"
    titles = {issue.title for issue in review.issues}
    assert "Не удалось уверенно понять товарную часть" in titles
    assert "Период анализа не указан явно" in titles


def test_review_brief_returns_ok_when_data_is_specific():
    brief = BriefData(
        name="ООО Фреш",
        inn_client=["5009138436"],
        analysis_period="range:2025-01-01:2025-01-31",
        product_words=["Фасадные панели"],
        regions=["Москва"],
    )

    excel_text = """
    Название компании заказчика | ООО Фреш
    ИНН заказчика | 5009138436
    Период анализа | с 01.01.2025 по 31.01.2025
    Потребляемая продукция | Фасадные панели
    """

    review = review_brief(excel_text, brief)

    assert review.status == "ok"
    assert [issue.severity for issue in review.issues] == []


def test_review_brief_flags_invalid_inn():
    brief = BriefData(
        name="ООО Фреш",
        inn_client=["1111111111"],
        analysis_period="range:2025-01-01:2025-01-31",
        product_words=["Пожарная сигнализация"],
        regions=["Москва"],
    )

    excel_text = """
    Название компании заказчика | ООО Фреш
    ИНН заказчика | 1111111111
    Период анализа | с 01.01.2025 по 31.01.2025
    Потребляемая продукция | Пожарная сигнализация
    """

    review = review_brief(excel_text, brief)

    assert review.status == "ok"
    titles = {issue.title for issue in review.issues}
    assert "ИНН заказчика выглядит некорректным" in titles
    assert [issue.severity for issue in review.issues] == ["recommendation"]


def test_review_brief_ignores_exclusion_inns_for_customer_inn_conflict():
    brief = BriefData(
        name="ООО Фреш",
        inn_client=["5009138436"],
        analysis_period="range:2025-01-01:2025-01-31",
        product_words=["Пожарная сигнализация"],
        regions=["Москва"],
        exclusions=["2536282880", "7460041175"],
    )

    excel_text = """
    Заказчик | ООО Фреш
    Реквизиты | ИНН 5009138436
    ИНН исключения | 2536282880, 7460041175
    Период анализа | с 01.01.2025 по 31.01.2025
    Потребляемая продукция | Пожарная сигнализация
    """

    review = review_brief(excel_text, brief)

    titles = {issue.title for issue in review.issues}
    assert "В брифе встречаются разные ИНН" not in titles
    assert review.status == "ok"


def test_review_brief_flags_client_name_mismatch():
    brief = BriefData(
        name="ООО Сбербанк",
        inn_client=["5009138436"],
        analysis_period="range:2025-01-01:2025-01-31",
        product_words=["Пожарная сигнализация"],
        regions=["Москва"],
    )

    excel_text = """
    Название компании заказчика | ООО Фреш
    ИНН заказчика | 5009138436
    Период анализа | с 01.01.2025 по 31.01.2025
    Потребляемая продукция | Пожарная сигнализация
    """

    review = review_brief(excel_text, brief)

    assert review.status == "needs_revision"
    titles = {issue.title for issue in review.issues}
    assert "Название заказчика определено неверно" in titles


def test_review_brief_does_not_block_on_generic_product_word_alone():
    brief = BriefData(
        name="ООО Фреш",
        inn_client=["5009138436"],
        analysis_period="range:2025-01-01:2025-01-31",
        product_words=["Оборудование"],
        regions=["Москва"],
    )

    excel_text = """
    Название компании заказчика | ООО Фреш
    ИНН заказчика | 5009138436
    Период анализа | с 01.01.2025 по 31.01.2025
    Потребляемая продукция | Оборудование
    """

    review = review_brief(excel_text, brief)

    assert review.status == "ok"
    assert [issue.severity for issue in review.issues] == ["recommendation"]
    assert review.issues[0].title == "Товарные формулировки слишком общие"


def test_review_brief_accepts_federal_district_without_regions():
    brief = BriefData(
        name="ООО Фреш",
        inn_client=["5009138436"],
        analysis_period="range:2025-01-01:2025-01-31",
        product_words=["Пожарная сигнализация"],
        f_ocrygs=["СФО"],
    )

    excel_text = """
    Название компании заказчика | ООО Фреш
    ИНН заказчика | 5009138436
    Период анализа | с 01.01.2025 по 31.01.2025
    Потребляемая продукция | Пожарная сигнализация
    """

    review = review_brief(excel_text, brief)

    titles = {issue.title for issue in review.issues}
    assert "Регион поиска не указан" not in titles


def test_review_brief_recommends_when_okved_context_exists_but_codes_missing():
    brief = BriefData(
        name="ООО Фреш",
        inn_client=["5009138436"],
        analysis_period="range:2025-01-01:2025-01-31",
        product_words=["Пожарная сигнализация"],
        regions=["Москва"],
        okved_list=[],
    )

    excel_text = """
    Название компании заказчика | ООО Фреш
    ИНН заказчика | 5009138436
    Целевая аудитория | монтажные организации и застройщики
    """

    review = review_brief(excel_text, brief)

    titles = {issue.title for issue in review.issues}
    assert "Не удалось уверенно определить ОКВЭД-фильтр" in titles
    assert review.status == "ok"


def test_review_brief_recommends_when_okved_codes_are_too_broad():
    brief = BriefData(
        name="ООО Фреш",
        inn_client=["5009138436"],
        analysis_period="range:2025-01-01:2025-01-31",
        product_words=["Пожарная сигнализация"],
        regions=["Москва"],
        okved_list=["41", "43.21"],
    )

    excel_text = """
    Название компании заказчика | ООО Фреш
    ИНН заказчика | 5009138436
    ОКВЭД | 41, 43.21
    """

    review = review_brief(excel_text, brief)

    titles = {issue.title for issue in review.issues}
    assert "ОКВЭД-фильтр получился слишком широким" in titles
    assert review.status == "ok"


def test_review_brief_warns_when_no_industry_restriction_conflicts_with_okved():
    brief = BriefData(
        name="ООО Фреш",
        inn_client=["5009138436"],
        analysis_period="range:2025-01-01:2025-01-31",
        product_words=["Пожарная сигнализация"],
        regions=["Москва"],
        okved_list=["43.21"],
    )

    excel_text = """
    Название компании заказчика | ООО Фреш
    ИНН заказчика | 5009138436
    Целевая аудитория | любые потребители указанной продукции
    """

    review = review_brief(excel_text, brief)

    titles = {issue.title for issue in review.issues}
    assert "ОКВЭД-фильтр противоречит формулировке брифа" in titles
    assert review.status == "ok"
    assert [issue.severity for issue in review.issues] == ["recommendation"]


def test_review_brief_exposes_okved_explanations_in_extracted_fields():
    brief = BriefData(
        name="ООО Фреш",
        inn_client=["5009138436"],
        analysis_period="range:2025-01-01:2025-01-31",
        product_words=["Пожарная сигнализация"],
        regions=["Москва"],
        okved_list=["43.21"],
        okved_explanations={"43.21": ["Семантический сигнал из брифа: 'монтажные организации'"]},
    )

    review = review_brief("Целевая аудитория | монтажные организации", brief)

    assert review.extracted_fields["okved_explanations"]["43.21"] == [
        "Семантический сигнал из брифа: 'монтажные организации'"
    ]
