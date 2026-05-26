import openpyxl
from unittest.mock import MagicMock

from src.okved_resolver import resolve_okved_list, resolve_okved_resolution


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


def _make_mock_client(response_text: str):
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = response_text
    mock_message = MagicMock()
    mock_message.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_message
    return mock_client


def test_resolve_okved_list_prefers_explicit_codes(tmp_path, monkeypatch):
    okved_path = tmp_path / "okved.xlsx"
    _write_okved_dict(okved_path)
    monkeypatch.setenv("OKVED_DICT_PATH", str(okved_path))

    result = resolve_okved_list("ОКВЭД | 46.11, 41.20")

    assert result == ["46.11", "41.20"]


def test_resolve_okved_resolution_keeps_explicit_code_explanations(tmp_path, monkeypatch):
    okved_path = tmp_path / "okved.xlsx"
    _write_okved_dict(okved_path)
    monkeypatch.setenv("OKVED_DICT_PATH", str(okved_path))

    result = resolve_okved_resolution("ОКВЭД | 46.11, 41.20")

    assert result.codes == ["46.11", "41.20"]
    assert result.decision_reason == "explicit_codes"
    assert result.explanations["46.11"] == ["Явно указан код ОКВЭД в брифе"]


def test_resolve_okved_list_returns_empty_for_any_consumers(tmp_path, monkeypatch):
    okved_path = tmp_path / "okved.xlsx"
    _write_okved_dict(okved_path)
    monkeypatch.setenv("OKVED_DICT_PATH", str(okved_path))

    result = resolve_okved_list(
        "Целевая аудитория | Любые потребители указанной продукции "
        "(монтажные организации, застройщики, УК, санатории)"
    )

    assert result == []


def test_resolve_okved_list_uses_manual_semantic_hints(tmp_path, monkeypatch):
    okved_path = tmp_path / "okved.xlsx"
    _write_okved_dict(okved_path)
    monkeypatch.setenv("OKVED_DICT_PATH", str(okved_path))

    result = resolve_okved_list(
        "Целевая аудитория | монтажные организации, застройщики, УК, санатории"
    )

    # Manual hint codes must all be present; embeddings may surface additional
    # candidates that the LLM reranker will narrow down in production.
    expected = {"41.20", "43.21", "43.29", "68.32.1", "68.32.2", "71.12.2", "86.90.4"}
    assert expected.issubset(set(result))


def test_resolve_okved_resolution_keeps_semantic_explanations(tmp_path, monkeypatch):
    okved_path = tmp_path / "okved.xlsx"
    _write_okved_dict(okved_path)
    monkeypatch.setenv("OKVED_DICT_PATH", str(okved_path))

    result = resolve_okved_resolution(
        "Целевая аудитория | монтажные организации, застройщики, УК, санатории"
    )

    assert "43.21" in result.explanations
    assert any("монтажные организации" in item for item in result.explanations["43.21"])
    assert "68.32.1" in result.explanations
    assert any("ук" in item.casefold() for item in result.explanations["68.32.1"])


def test_resolve_okved_list_uses_llm_rerank_for_ambiguous_candidates(tmp_path, monkeypatch):
    okved_path = tmp_path / "okved.xlsx"
    _write_okved_dict(okved_path)
    monkeypatch.setenv("OKVED_DICT_PATH", str(okved_path))
    client = _make_mock_client('["68.32.1"]')

    result = resolve_okved_list(
        "Целевая аудитория | управляющие компании",
        client=client,
        model="test-model",
    )

    assert result == ["68.32.1"]
    _, kwargs = client.chat.completions.create.call_args
    assert kwargs["model"] == "test-model"
    assert "Кандидаты ОКВЭД" in kwargs["messages"][1]["content"]


def test_resolve_okved_list_skips_llm_for_no_filter_signal(tmp_path, monkeypatch):
    okved_path = tmp_path / "okved.xlsx"
    _write_okved_dict(okved_path)
    monkeypatch.setenv("OKVED_DICT_PATH", str(okved_path))
    client = _make_mock_client('["43.21"]')

    result = resolve_okved_list(
        "Целевая аудитория | любые потребители указанной продукции, включая монтажные организации",
        client=client,
        model="test-model",
    )

    assert result == []
    client.chat.completions.create.assert_not_called()
