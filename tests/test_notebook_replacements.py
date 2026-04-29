import nbformat

from src.models import BriefData
from src.notebook_replacements import build_replacements
from src.settings import DEFAULT_TEMPLATE_PATH


def test_replacement_markers_match_template():
    brief = BriefData(
        name="ООО Фреш",
        inn_client=["5009138436"],
        analysis_period="last_N_months:6",
    )
    replacements = build_replacements(brief, "2025-09-17", "2026-03-17", [], [])

    nb = nbformat.read(DEFAULT_TEMPLATE_PATH, as_version=4)
    template_markers = {
        cell.source.split("\n", 1)[0].strip()[2:].strip()
        for cell in nb.cells
        if cell.cell_type == "code" and cell.source.startswith("# ##AGENT:")
    }

    assert set(replacements) == template_markers
