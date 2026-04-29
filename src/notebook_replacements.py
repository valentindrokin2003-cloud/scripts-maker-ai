from pathlib import Path
from string import Template

from src.models import BriefData
from src.settings import DEFAULT_NOTEBOOK_BLOCKS_DIR


MARKER_TEMPLATES = {
    "##AGENT:name##": "name.py",
    "##AGENT:inn_client##": "inn_client.py",
    "##AGENT:date_filter##": "date_filter.py",
    "##AGENT:date_filter2##": "date_filter2.py",
    "##AGENT:lst_sbersov##": "lst_sbersov.py",
    "##AGENT:list_words##": "list_words.py",
    "##AGENT:regions_filter##": "regions_filter.py",
    "##AGENT:okved_list##": "okved_list.py",
    "##AGENT:exclusions##": "exclusions.py",
    "##AGENT:revenue##": "revenue.py",
    "##AGENT:trans_thresholds##": "trans_thresholds.py",
}


def _number_repr(value: int) -> str:
    return f"{value:_}"


def _format_regex_patterns(patterns: list[str]) -> str:
    if not patterns:
        return "[]"
    return "[\n" + "".join(f"    {_regex_literal(pattern)},\n" for pattern in patterns) + "]"


def _regex_literal(pattern: str) -> str:
    """Render regex as readable Python source while preserving exact value."""
    if not pattern.endswith("\\"):
        if "'" not in pattern:
            return f"r'{pattern}'"
        if '"' not in pattern:
            return f'r"{pattern}"'
    return repr(pattern)


def _render_block(filename: str, values: dict, blocks_dir: str) -> str:
    path = Path(blocks_dir) / filename
    source = path.read_text(encoding="utf-8")
    return Template(source).substitute(values)


def build_replacements(
    brief: BriefData,
    start_date: str,
    end_date: str,
    lst_sbersov: list[str],
    list_words: list[str],
    blocks_dir: str = DEFAULT_NOTEBOOK_BLOCKS_DIR,
) -> dict:
    okved_filter_line = "    .filter(F.col('okved_original_version') == 2)\\\n"
    if brief.okved_list:
        okved_filter_line += "    .filter(F.col('okved').isin(okved_list))\\\n"

    if brief.revenue_max is not None:
        revenue_filter_block = (
            f"end_rev = {_number_repr(brief.revenue_max)}\n"
            "revenue_filtered = revenue_2022_2023.filter(\n"
            "    (F.col('revenue') >= start_rev) & (F.col('revenue') <= end_rev)\n"
            ")"
        )
    else:
        revenue_filter_block = (
            "revenue_filtered = revenue_2022_2023.filter(F.col('revenue') >= start_rev)"
        )

    values = {
        "name_repr": repr(brief.name),
        "inn_client_repr": repr(brief.inn_client),
        "start_date_repr": repr(start_date),
        "end_date_repr": repr(end_date),
        "lst_sbersov_repr": repr(lst_sbersov),
        "list_words_repr": _format_regex_patterns(list_words),
        "regions_repr": repr(brief.regions),
        "f_ocrygs_repr": repr(brief.f_ocrygs),
        "okved_list_repr": repr(brief.okved_list),
        "okved_filter_line": okved_filter_line,
        "exclusions_repr": repr(brief.exclusions or []),
        "revenue_min": _number_repr(brief.revenue_min),
        "revenue_filter_block": revenue_filter_block,
        "trans_sum_min": _number_repr(brief.trans_sum_min),
        "trans_cnt_min": brief.trans_cnt_min,
    }

    return {
        marker: _render_block(filename, values, blocks_dir)
        for marker, filename in MARKER_TEMPLATES.items()
    }
