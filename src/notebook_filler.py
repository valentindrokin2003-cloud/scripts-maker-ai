import warnings
import nbformat
from typing import Dict


class MarkerNotFoundWarning(UserWarning):
    pass


def fill_notebook(nb: nbformat.NotebookNode, replacements: Dict[str, str]) -> None:
    """
    Replace cells in a notebook in-place.
    replacements: {marker_string: new_cell_source}
    Each marker is matched against the first line of each code cell.
    Missing markers emit a MarkerNotFoundWarning.
    """
    found = set()

    for cell in nb.cells:
        if cell.cell_type != "code":
            continue
        first_line = cell.source.split("\n")[0].strip()
        for marker, new_source in replacements.items():
            if marker in first_line:
                cell.source = new_source
                found.add(marker)
                break

    for marker in replacements:
        if marker not in found:
            warnings.warn(
                f"Marker '{marker}' not found in template notebook. Cell was not filled.",
                MarkerNotFoundWarning,
            )


def load_template(template_path: str) -> nbformat.NotebookNode:
    with open(template_path, encoding="utf-8") as f:
        return nbformat.read(f, as_version=4)


def save_notebook(nb: nbformat.NotebookNode, output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)
