import pytest
from unittest.mock import MagicMock
from src.brief_extractor import extract_brief, BriefExtractionError
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
    mock_client = MagicMock()
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=response_text)]
    mock_client.messages.create.return_value = mock_msg
    return mock_client


def test_extract_brief_returns_briefdata():
    client = _make_mock_client(VALID_JSON)
    result = extract_brief("some excel text", client)
    assert isinstance(result, BriefData)
    assert result.name == "ООО Фреш"
    assert result.inn_client == ["5009138436"]
    assert result.revenue_max is None


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
