import json
from typing import Any


class LLMJsonError(ValueError):
    pass


def strip_markdown_json(raw: str) -> str:
    """Return JSON text from a raw LLM response, tolerating fenced blocks."""
    text = raw.strip()
    if not text.startswith("```"):
        return text

    parts = text.split("```", 2)
    if len(parts) < 2:
        return text

    fenced = parts[1].strip()
    if fenced.lower().startswith("json"):
        fenced = fenced[4:].strip()
    return fenced


def parse_llm_json(raw: str) -> Any:
    text = strip_markdown_json(raw)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMJsonError(str(exc)) from exc
