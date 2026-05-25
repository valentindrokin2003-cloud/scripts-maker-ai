import re
from unittest.mock import MagicMock
from src.regex_generator import generate_regex


def _make_mock_client(response_text: str):
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = response_text
    mock_msg = MagicMock()
    mock_msg.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_msg
    return mock_client


# ── Basic contract ────────────────────────────────────────────────────────────

def test_generate_regex_returns_list():
    spec = '{"concepts": [{"base_word": "фасад", "pos": "noun", "standalone": true, "pairs": []}]}'
    client = _make_mock_client(spec)
    result = generate_regex(["Фасадные кассеты"], client)
    assert isinstance(result, list)


def test_generate_regex_sends_system_message():
    spec = '{"concepts": [{"base_word": "фасад", "pos": "noun", "standalone": true, "pairs": []}]}'
    client = _make_mock_client(spec)
    generate_regex(["Фасадные кассеты"], client, model="custom-model")
    _, kwargs = client.chat.completions.create.call_args
    assert kwargs["model"] == "custom-model"
    assert kwargs["messages"][0]["role"] == "system"


def test_generate_regex_produces_valid_patterns():
    spec = '{"concepts": [{"base_word": "фасад", "pos": "noun", "standalone": false, "pairs": [{"with": "кассета"}]}, {"base_word": "кассета", "pos": "noun", "standalone": false, "pairs": []}]}'
    client = _make_mock_client(spec)
    result = generate_regex(["Фасадные кассеты"], client)
    for pattern in result:
        re.compile(pattern)


def test_empty_product_words_returns_empty():
    client = _make_mock_client("{}")
    result = generate_regex([], client)
    assert result == []
    client.chat.completions.create.assert_not_called()


# ── Fallback behaviour ────────────────────────────────────────────────────────

def test_invalid_json_falls_back_to_local_seeds(caplog):
    client = _make_mock_client("не JSON")
    result = generate_regex(["слово"], client)
    assert "JSON parse error" in caplog.text
    assert result == [r"\bслово\w{0,3}\b"]


def test_missing_concepts_key_falls_back_to_local_seeds(caplog):
    client = _make_mock_client('{"pattern": "\\\\bпанел\\\\b"}')
    result = generate_regex(["панель"], client)
    assert "missing 'concepts'" in caplog.text
    assert result == [r"\bпанн?ел\w{0,3}\b"]


def test_api_error_falls_back_to_local_seeds(caplog):
    client = MagicMock()
    client.chat.completions.create.side_effect = ConnectionError("no network")
    result = generate_regex(["кассета"], client)
    assert isinstance(result, list)
    # At minimum the local seed pattern must be present
    assert any("кассет" in p for p in result)


# ── Merge and integration ─────────────────────────────────────────────────────

def test_stage2_patterns_included_in_result():
    spec = '{"concepts": [{"base_word": "бухгалтерский", "pos": "adj", "standalone": false, "pairs": [{"with": "услуга"}]}, {"base_word": "услуга", "pos": "noun", "standalone": false, "pairs": []}]}'
    client = _make_mock_client(spec)
    result = generate_regex(["бухгалтерские услуги"], client)
    assert any("бухгалтерск" in p for p in result)


def test_local_seed_patterns_merged_with_stage2():
    # "шины для экскаватора" triggers _tire_patterns → local seeds include "скават"
    spec = '{"concepts": [{"base_word": "семинар", "pos": "noun", "standalone": true, "pairs": []}]}'
    client = _make_mock_client(spec)
    result = generate_regex(["шины для экскаватора"], client)
    assert any("скават" in p for p in result)    # from local seeds
    assert any("семинар" in p for p in result)   # from stage2


def test_stage2_pair_pattern_present_after_merge():
    """Stage 2 pair patterns (free endings) are preserved after normalize()."""
    spec = '{"concepts": [{"base_word": "выездной", "pos": "adj", "standalone": false, "ambiguous": false, "pairs": [{"with": "семинар"}]}, {"base_word": "семинар", "pos": "noun", "standalone": false, "ambiguous": false, "pairs": []}]}'
    client = _make_mock_client(spec)
    result = generate_regex(["выездной семинар"], client)
    # Stage 2 emits a grouped pair pattern: выездн...[-/ ]*семинар...
    assert any("выездн" in p and "семинар" in p for p in result)
    # All patterns are valid regex
    import re
    for p in result:
        re.compile(p)
