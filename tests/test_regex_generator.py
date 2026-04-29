import re
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

    generate_regex(["Фасадные кассеты"], client, model="custom-model")

    _, kwargs = client.chat.completions.create.call_args
    assert "system_prompt" not in kwargs
    assert kwargs["model"] == "custom-model"
    assert kwargs["messages"][0]["role"] == "system"


def test_generate_regex_all_valid_patterns():
    client = _make_mock_client('["\\\\bфасадн\\\\w{0,3}\\\\b", "\\\\bкассет\\\\w{0,3}\\\\b"]')
    result = generate_regex(["Фасадные кассеты"], client)
    for pattern in result:
        re.compile(pattern)  # should not raise


def test_generate_regex_invalid_pattern_is_dropped(caplog):
    client = _make_mock_client('["\\\\bвалидн\\\\w\\\\b", "[невалидная регулярка"]')
    result = generate_regex(["тест"], client)
    assert "Invalid regex pattern" in caplog.text
    assert r"\bвалидн\w\b" in result


def test_empty_product_words_returns_empty():
    client = _make_mock_client("[]")
    result = generate_regex([], client)
    assert result == []


def test_invalid_json_returns_empty(caplog):
    client = _make_mock_client("не JSON")
    result = generate_regex(["слово"], client)
    assert "Returning local seed patterns due to invalid JSON" in caplog.text
    assert result == [r"\bслово\w{0,3}\b"]


def test_non_list_json_returns_empty(caplog):
    client = _make_mock_client('{"pattern": "\\\\bпанел\\\\b"}')
    result = generate_regex(["панель"], client)
    assert "Expected JSON array" in caplog.text
    assert result == [r"\bпанн?ел\w{0,3}\b"]


def test_generate_regex_merges_local_and_llm_patterns():
    client = _make_mock_client('["\\\\bllm\\\\b"]')
    result = generate_regex(["шины для экскаватора"], client)

    assert r"\bllm\b" in result
    assert any("скават" in pattern for pattern in result)
