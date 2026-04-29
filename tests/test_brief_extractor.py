import pytest
from unittest.mock import MagicMock
import openpyxl
from src.brief_extractor import (
    _extract_product_words_from_excel_text,
    extract_brief,
    BriefExtractionError,
)
from src.brief_source import extract_client_inns_from_excel_text
from src.models import BriefData


VALID_JSON = '''{
  "name": "ООО Фреш",
  "inn_client": ["5009138436"],
  "analysis_period": "last_N_months:6",
  "product_words": ["Фасадные панели"],
  "regions": ["Москва"],
  "okved_list": ["46.11"],
  "exclusions": [],
  "revenue_min": 1000000,
  "revenue_max": null,
  "trans_sum_min": 10000000,
  "trans_cnt_min": 3
}'''


def _make_mock_client(response_text: str):
    """Create mock OpenAI client for DeepSeek API"""
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = response_text
    mock_msg = MagicMock()
    mock_msg.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_msg
    return mock_client


def _write_okved_dict(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "ОКВЭД 2"
    ws.append(("ОКВЭД 2 — Общероссийский классификатор видов экономической деятельности",))
    ws.append(())
    ws.append(("№", "Код", "Название"))
    ws.append((1, "41.20", "Строительство жилых и нежилых зданий"))
    ws.append((2, "43.21", "Производство электромонтажных работ"))
    ws.append((3, "43.29", "Производство прочих строительно-монтажных работ"))
    ws.append((4, "68.32.1", "Управление эксплуатацией жилого фонда за вознаграждение или на договорной основе"))
    ws.append((5, "68.32.2", "Управление эксплуатацией нежилого фонда за вознаграждение или на договорной основе"))
    ws.append((6, "71.12.2", "Деятельность заказчика-застройщика, генерального подрядчика"))
    ws.append((7, "86.90.4", "Деятельность санаторно-курортных организаций"))
    ws.append((8, "46.11", "Деятельность агентов по оптовой торговле сельскохозяйственным сырьем"))
    wb.save(path)


def test_extract_brief_returns_briefdata():
    client = _make_mock_client(VALID_JSON)
    result = extract_brief("some excel text", client)
    assert isinstance(result, BriefData)
    assert result.name == "ООО Фреш"
    assert result.inn_client == ["5009138436"]
    assert result.revenue_max is None
    assert result.regions == ["Москва"]
    assert result.f_ocrygs == []


def test_extract_brief_splits_regions_and_federal_districts():
    json_text = VALID_JSON.replace('"regions": ["Москва"]', '"regions": ["Новосибирск", "ЦФО"]')
    client = _make_mock_client(json_text)

    result = extract_brief("some excel text", client)

    assert result.regions == ["Новосибирская область"]
    assert result.f_ocrygs == ["ЦФО"]


def test_extract_brief_sends_system_prompt_as_system_message():
    client = _make_mock_client(VALID_JSON)

    extract_brief("some excel text", client, model="custom-model")

    _, kwargs = client.chat.completions.create.call_args
    assert "system_prompt" not in kwargs
    assert kwargs["model"] == "custom-model"
    assert kwargs["messages"][0]["role"] == "system"
    assert kwargs["messages"][1] == {"role": "user", "content": "some excel text"}


def test_extract_brief_missing_name_raises():
    bad_json = '{"inn_client": ["123"], "analysis_period": "last_N_months:6"}'
    client = _make_mock_client(bad_json)
    with pytest.raises(BriefExtractionError, match="name"):
        extract_brief("excel text", client)


def test_extract_brief_missing_inn_raises():
    bad_json = '{"name": "Test", "analysis_period": "last_N_months:6"}'
    client = _make_mock_client(bad_json)
    with pytest.raises(BriefExtractionError, match="inn_client"):
        extract_brief("excel text", client)


def test_extract_brief_invalid_json_raises():
    client = _make_mock_client("not json at all")
    with pytest.raises(BriefExtractionError):
        extract_brief("excel text", client)


def test_extract_brief_prefers_source_product_row_over_llm_shortening():
    json_text = VALID_JSON.replace(
        '"product_words": ["Фасадные панели"]',
        '"product_words": ["коннекторы", "нить", "разъемы"]',
    )
    client = _make_mock_client(json_text)
    excel_text = (
        "=== Лист: ТЗ ===\n"
        "Потребляемая продукция | коннекторы светильников, "
        "вольфрамовая нить, промышленые разъемы\n"
    )

    result = extract_brief(excel_text, client)

    assert result.product_words == [
        "коннекторы светильников",
        "вольфрамовая нить",
        "промышленые разъемы",
    ]


def test_extract_product_words_keeps_commas_inside_parentheses():
    excel_text = (
        "=== Лист: ТЗ ===\n"
        "Потребляемая продукция | ASIC-майнеры (Antminer, Whatsminer), "
        "вычислительное серверное оборудование\n"
    )

    assert _extract_product_words_from_excel_text(excel_text) == [
        "ASIC-майнеры (Antminer, Whatsminer)",
        "вычислительное серверное оборудование",
    ]


def test_extract_product_words_keeps_multiline_cell_continuations():
    excel_text = (
        "=== Лист: ТЗ ===\n"
        "Потребляемая продукция | Протеиновые напитки (Neo, Shock)\n"
        "Сухие смеси для приготовления протеиновых напитков\n"
        "Растительные протеиновые напитки\n"
        "Регион | Москва\n"
    )

    assert _extract_product_words_from_excel_text(excel_text) == [
        "Протеиновые напитки (Neo, Shock)",
        "Сухие смеси для приготовления протеиновых напитков",
        "Растительные протеиновые напитки",
    ]


def test_extract_brief_prefers_explicit_client_fields_from_excel():
    json_text = VALID_JSON.replace('"name": "ООО Фреш"', '"name": "ООО Сбербанк"').replace(
        '"inn_client": ["5009138436"]',
        '"inn_client": ["1111111111"]',
    )
    client = _make_mock_client(json_text)
    excel_text = (
        "=== Лист: ТЗ ===\n"
        "Название компании заказчика | ООО Фреш\n"
        "ИНН заказчика | 5009138436\n"
    )

    result = extract_brief(excel_text, client)

    assert result.name == "ООО Фреш"
    assert result.inn_client == ["5009138436"]


def test_extract_client_inns_ignores_exclusion_labels():
    excel_text = (
        "=== Лист: ТЗ ===\n"
        "ИНН заказчика | 5009138436\n"
        "ИНН заказчика исключения | 2536282880, 7460041175\n"
    )

    assert extract_client_inns_from_excel_text(excel_text) == ["5009138436"]


def test_extract_brief_ignores_exclusion_inns_in_explicit_client_field_overlay():
    json_text = VALID_JSON.replace('"inn_client": ["5009138436"]', '"inn_client": ["1111111111"]')
    client = _make_mock_client(json_text)
    excel_text = (
        "=== Лист: ТЗ ===\n"
        "Название компании заказчика | ООО Фреш\n"
        "ИНН заказчика | 5009138436\n"
        "ИНН заказчика исключения | 2536282880, 7460041175\n"
    )

    result = extract_brief(excel_text, client)

    assert result.inn_client == ["5009138436"]


def test_extract_brief_resolves_okved_from_semantic_context(tmp_path, monkeypatch):
    okved_path = tmp_path / "okved.xlsx"
    _write_okved_dict(okved_path)
    monkeypatch.setenv("OKVED_DICT_PATH", str(okved_path))

    json_text = VALID_JSON.replace('"okved_list": ["46.11"]', '"okved_list": []')
    client = _make_mock_client(json_text)
    excel_text = (
        "=== Лист: ТЗ ===\n"
        "Целевая аудитория | монтажные организации, застройщики, УК, санатории\n"
    )

    result = extract_brief(excel_text, client)

    assert set(result.okved_list) == {
        "41.20",
        "43.21",
        "43.29",
        "68.32.1",
        "68.32.2",
        "71.12.2",
        "86.90.4",
    }
    assert "43.21" in result.okved_explanations
    assert any("монтажные организации" in item for item in result.okved_explanations["43.21"])


def test_extract_brief_skips_okved_when_any_consumers_are_requested(tmp_path, monkeypatch):
    okved_path = tmp_path / "okved.xlsx"
    _write_okved_dict(okved_path)
    monkeypatch.setenv("OKVED_DICT_PATH", str(okved_path))

    json_text = VALID_JSON.replace('"okved_list": ["46.11"]', '"okved_list": []')
    client = _make_mock_client(json_text)
    excel_text = (
        "=== Лист: ТЗ ===\n"
        "Целевая аудитория | Любые потребители указанной продукции "
        "(монтажные организации, застройщики, УК, санатории)\n"
    )

    result = extract_brief(excel_text, client)

    assert result.okved_list == []
    assert result.okved_explanations == {}
