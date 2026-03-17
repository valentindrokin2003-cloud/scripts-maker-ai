import nbformat
import pytest
from src.notebook_filler import fill_notebook, MarkerNotFoundWarning
import warnings


def _make_nb_with_marker(marker: str, placeholder: str) -> nbformat.NotebookNode:
    nb = nbformat.v4.new_notebook()
    nb.cells = [nbformat.v4.new_code_cell(f"# {marker}\n{placeholder}")]
    return nb


def test_fill_replaces_marker_cell():
    nb = _make_nb_with_marker("##AGENT:name##", "name = ''")
    replacements = {"##AGENT:name##": "# ##AGENT:name##\nname = 'ООО Фреш'"}
    fill_notebook(nb, replacements)
    assert "name = 'ООО Фреш'" in nb.cells[0].source


def test_fill_multiple_markers():
    nb = nbformat.v4.new_notebook()
    nb.cells = [
        nbformat.v4.new_code_cell("# ##AGENT:name##\nname = ''"),
        nbformat.v4.new_code_cell("# ##AGENT:inn_client##\ninn_client = []"),
    ]
    replacements = {
        "##AGENT:name##": "# ##AGENT:name##\nname = 'Test'",
        "##AGENT:inn_client##": "# ##AGENT:inn_client##\ninn_client = ['123']",
    }
    fill_notebook(nb, replacements)
    assert "name = 'Test'" in nb.cells[0].source
    assert "inn_client = ['123']" in nb.cells[1].source


def test_missing_marker_warns():
    nb = nbformat.v4.new_notebook()
    nb.cells = [nbformat.v4.new_code_cell("# some other cell\nx = 1")]
    replacements = {"##AGENT:name##": "name = 'X'"}
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        fill_notebook(nb, replacements)
    assert any("##AGENT:name##" in str(warning.message) for warning in w)


def test_does_not_modify_unrelated_cells():
    nb = nbformat.v4.new_notebook()
    nb.cells = [
        nbformat.v4.new_code_cell("# ##AGENT:name##\nname = ''"),
        nbformat.v4.new_code_cell("import pandas as pd"),
    ]
    fill_notebook(nb, {"##AGENT:name##": "# ##AGENT:name##\nname = 'X'"})
    assert "import pandas as pd" in nb.cells[1].source
