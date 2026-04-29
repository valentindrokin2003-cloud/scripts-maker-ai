import pytest

from src.llm_json import LLMJsonError, parse_llm_json, strip_markdown_json


def test_strip_markdown_json_handles_plain_json():
    assert strip_markdown_json('{"a": 1}') == '{"a": 1}'


def test_strip_markdown_json_handles_fenced_json():
    raw = '```json\n{"a": 1}\n```'
    assert strip_markdown_json(raw) == '{"a": 1}'


def test_parse_llm_json_handles_fenced_json():
    raw = '```json\n["one", "two"]\n```'
    assert parse_llm_json(raw) == ["one", "two"]


def test_parse_llm_json_wraps_decode_error():
    with pytest.raises(LLMJsonError):
        parse_llm_json("not json")
