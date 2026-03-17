import openpyxl
import pytest
from src.words_matcher import match_words


@pytest.fixture
def dict_xlsx(tmp_path):
    path = tmp_path / "words.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Группа1"
    ws["A1"] = "Панель"
    ws["A2"] = "Фасад"
    ws["A3"] = "Кассета"
    ws["A4"] = "Труба"
    wb.save(path)
    return str(path)


def test_exact_match(dict_xlsx):
    result = match_words(["Панель", "Труба"], dict_xlsx)
    assert "Панель" in result
    assert "Труба" in result


def test_fuzzy_match(dict_xlsx):
    result = match_words(["Панели"], dict_xlsx)
    assert "Панель" in result


def test_no_match_returns_empty(dict_xlsx):
    result = match_words(["Экскаватор"], dict_xlsx)
    assert result == []


def test_returns_dict_words_not_input_words(dict_xlsx):
    result = match_words(["Фасадные"], dict_xlsx)
    assert "Фасад" in result
    assert "Фасадные" not in result


def test_deduplication(dict_xlsx):
    result = match_words(["Панель", "Панели"], dict_xlsx)
    assert result.count("Панель") == 1
