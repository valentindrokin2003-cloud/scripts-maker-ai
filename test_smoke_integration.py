#!/usr/bin/env python3
"""
Smoke test for B2B Script Agent — tests end-to-end integration with mocked Claude API.
Verifies that all notebook markers are filled correctly with realistic data.
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import nbformat

from src.brief_extractor import BriefData
from src.date_resolver import resolve_dates
from src.excel_parser import parse_excel_to_text
from src.notebook_filler import fill_notebook, load_template, save_notebook
from src.regex_generator import generate_regex
from src.words_matcher import match_words
from agent import build_replacements

TEMPLATE_PATH = "templates/b2b_template.ipynb"
DICT_PATH = "data/words_ok_groups_v2.xlsx"
BRIEF_PATH = "data/ТЗ по подбору В2В- ООО Фреш.xlsx"
OUTPUT_PATH = "output/test_smoke_output.ipynb"


def mock_claude_field_extraction():
    """Mock Claude's field extraction response."""
    return BriefData(
        name="ООО Фреш",
        inn_client=["5009138436"],
        analysis_period="last_N_months:6",
        product_words=["Панель", "Фасад"],
        regions=["Московская область"],
        okved_list=["45.23"],
        exclusions=["7722406860"],
        revenue_min=100_000_000,
        revenue_max=500_000_000,
        trans_sum_min=10_000_000,
        trans_cnt_min=3,
    )


def mock_claude_regex_generation(product_words):
    """Mock Claude's regex generation response."""
    return [
        r"\bфасадн\w{0,3}[-/ ]*кассет\w{0,3}\b",
        r"\bкассет\w{0,3}[-/ ]*фасадн\w{0,3}\b",
        r"\bпанел\w{0,3}[-/ ]*алюмини\w{0,3}\b",
        r"\bалюмини\w{0,3}[-/ ]*панел\w{0,3}\b",
    ]


def test_smoke_integration():
    """Run end-to-end integration test with realistic data."""
    print("\n=== B2B Script Agent Smoke Test ===\n")

    # Step 1: Read Excel (real)
    print("[1/6] Reading Excel brief...")
    if not Path(BRIEF_PATH).exists():
        print(f"❌ Brief file not found: {BRIEF_PATH}")
        return False
    excel_text = parse_excel_to_text(BRIEF_PATH)
    print(f"✓ Read {len(excel_text)} chars from Excel")

    # Step 2: Extract fields (mocked Claude call 1)
    print("[2/6] Extracting fields (mocked)...")
    brief = mock_claude_field_extraction()
    print(f"✓ Extracted: name={brief.name!r}, inn_client={brief.inn_client}")

    # Step 3: Resolve dates (real)
    print("[3/6] Resolving dates...")
    start_date, end_date = resolve_dates(brief.analysis_period)
    print(f"✓ Dates: {start_date} to {end_date}")

    # Step 4: Match words (real)
    print("[4/6] Matching product words...")
    lst_sbersov = match_words(brief.product_words, DICT_PATH)
    print(f"✓ Matched words: {lst_sbersov}")

    # Step 5: Generate regex (mocked Claude call 2)
    print("[5/6] Generating regex patterns (mocked)...")
    list_words = mock_claude_regex_generation(brief.product_words)
    print(f"✓ Generated {len(list_words)} regex patterns")

    # Step 6: Fill notebook (real)
    print("[6/6] Filling notebook template...")
    replacements = build_replacements(brief, start_date, end_date, lst_sbersov, list_words)

    nb = load_template(TEMPLATE_PATH)
    fill_notebook(nb, replacements)  # modifies nb in-place
    save_notebook(nb, OUTPUT_PATH)
    print(f"✓ Saved to {OUTPUT_PATH}")

    # Verification: Check that all expected values are present
    print("\n=== Verification ===\n")
    nb = nbformat.read(OUTPUT_PATH, as_version=4)

    # Check for expected filled values (not just markers)
    expected_values = {
        "name": "ООО Фреш",
        "inn_client": "5009138436",
        "start_date": "2025-09-17",
        "end_date": "2026-03-17",
        "regions": "Московская область",
        "revenue_min": "100_000_000",
        "revenue_max": "500_000_000",
        "trans_sum_min": "10_000_000",
        "trans_cnt_min": "3",
    }

    found_values = {}
    notebook_text = "\n".join(cell.get("source", "") for cell in nb.cells)

    for key, value in expected_values.items():
        if value in notebook_text:
            found_values[key] = True

    missing = [k for k in expected_values if k not in found_values]

    if missing:
        print("❌ MISSING EXPECTED VALUES:")
        for key in missing:
            print(f"   {key}: {expected_values[key]}")
        return False

    print(f"✓ All {len(found_values)}/8 expected values found in notebook")

    # Count markers that are present (markers are supposed to be there with values)
    markers_present = sum(
        1 for marker in [
            "##AGENT:name##",
            "##AGENT:inn_client##",
            "##AGENT:date_filter##",
            "##AGENT:date_filter2##",
            "##AGENT:lst_sbersov##",
            "##AGENT:list_words##",
            "##AGENT:regions##",
            "##AGENT:okved_list##",
            "##AGENT:exclusions##",
            "##AGENT:revenue##",
            "##AGENT:trans_thresholds##",
        ]
        if marker in notebook_text
    )
    print(f"✓ {markers_present}/11 markers present with values\n")

    # Sample output
    print("Sample filled values:")
    for i, cell in enumerate(nb.cells):
        source = cell.get("source", "")
        if "name = " in source and "ООО Фреш" in source:
            print(f"  - name: {source.strip()[:60]}...")
            break

    for i, cell in enumerate(nb.cells):
        source = cell.get("source", "")
        if "inn_client = " in source and "5009138436" in source:
            print(f"  - inn_client: {source.strip()[:60]}...")
            break

    print("\n✅ SMOKE TEST PASSED")
    return True


if __name__ == "__main__":
    success = test_smoke_integration()
    sys.exit(0 if success else 1)
