import re
import pytest
from unittest.mock import MagicMock
from src.regex_generator import generate_regex


def _make_mock_client(response_text: str):
    """Create mock OpenAI client for DeepSeek API"""
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = response_text
    mock_msg = MagicMock()
    mock_msg.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_msg
    return mock_client


def test_generate_regex_returns_list():
    client = _make_mock_client('["\\\\bфасадн\\\\w{0,3}\\\\b"]')
    result = generate_regex(["Фасадные кассеты"], client)
    assert isinstance(result, list)


def test_generate_regex_sends_system_prompt_as_system_message():
    client = _make_mock_client('["\\\\bфасадн\\\\w{0,3}\\\\b"]')

    generate_regex(["Фасадные кассеты"], client)

    _, kwargs = client.chat.completions.create.call_args
    assert "system_prompt" not in kwargs
    assert kwargs["messages"][0]["role"] == "system"


def test_generate_regex_all_valid_patterns():
    client = _make_mock_client('["\\\\bфасадн\\\\w{0,3}\\\\b", "\\\\bкассет\\\\w{0,3}\\\\b"]')
    result = generate_regex(["Фасадные кассеты"], client)
    for pattern in result:
        re.compile(pattern)  # should not raise


def test_generate_regex_invalid_pattern_is_dropped(capsys):
    client = _make_mock_client('["\\\\bвалидн\\\\w\\\\b", "[невалидная регулярка"]')
    result = generate_regex(["тест"], client)
    out = capsys.readouterr().out
    assert "Warning" in out
    assert len(result) == 1


def test_empty_product_words_returns_empty():
    client = _make_mock_client("[]")
    result = generate_regex([], client)
    assert result == []


def test_invalid_json_returns_empty(capsys):
    client = _make_mock_client("не JSON")
    result = generate_regex(["слово"], client)
    out = capsys.readouterr().out
    assert "Warning" in out
    assert result == []
