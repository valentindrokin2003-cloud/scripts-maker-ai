#!/usr/bin/env python3
"""Smoke test for B2B Script Agent with mocked LLM calls."""
import sys
from pathlib import Path

import nbformat
import openpyxl

from src.brief_extractor import BriefData
from src.pipeline import run_pipeline
from src.settings import AgentSettings

TEMPLATE_PATH = "templates/b2b_template.ipynb"
DICT_PATH = "data/words_ok_groups_v2.xlsx"


def make_minimal_brief_xlsx(path: Path) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Бриф"
    rows = [
        ("Название компании заказчика", "ООО Фреш"),
        ("ИНН заказчика", "5009138436"),
        ("Период анализа", "с 2025-09-17 по 2026-03-17"),
        ("Потребляемая продукция", "Панель, Фасад"),
        ("Регионы", "Московская область"),
        ("ОКВЭД", "45.23"),
        ("Исключения", "7722406860"),
        ("Выручка", "100000000-500000000"),
        ("Сумма транзакций", "10000000"),
        ("Количество транзакций", "3"),
    ]
    for row in rows:
        ws.append(row)
    wb.save(path)


def mock_llm_field_extraction(excel_text, client, model):
    """Mock the LLM field extraction response."""
    assert "ООО Фреш" in excel_text
    assert "5009138436" in excel_text
    return BriefData(
        name="ООО Фреш",
        inn_client=["5009138436"],
        analysis_period="range:2025-09-17:2026-03-17",
        product_words=["Панель", "Фасад"],
        regions=["Московская область"],
        okved_list=["45.23"],
        exclusions=["7722406860"],
        revenue_min=100_000_000,
        revenue_max=500_000_000,
        trans_sum_min=10_000_000,
        trans_cnt_min=3,
    )


def mock_llm_regex_generation(product_words, client, model):
    """Mock the LLM regex generation response."""
    assert product_words == ["Панель", "Фасад"]
    return [
        r"\bфасадн\w{0,3}[-/ ]*кассет\w{0,3}\b",
        r"\bкассет\w{0,3}[-/ ]*фасадн\w{0,3}\b",
        r"\bпанел\w{0,3}[-/ ]*алюмини\w{0,3}\b",
        r"\bалюмини\w{0,3}[-/ ]*панел\w{0,3}\b",
    ]


def test_smoke_integration(tmp_path):
    """Run end-to-end integration test with realistic data."""
    print("\n=== B2B Script Agent Smoke Test ===\n")

    brief_path = tmp_path / "brief.xlsx"
    output_dir = tmp_path / "output"
    make_minimal_brief_xlsx(brief_path)

    settings = AgentSettings(
        api_key=None,
        template_path=TEMPLATE_PATH,
        dict_path=DICT_PATH,
        output_dir=str(output_dir),
    )
    result = run_pipeline(
        str(brief_path),
        str(output_dir),
        settings,
        client=None,
        progress=print,
        brief_extractor=mock_llm_field_extraction,
        regex_generator=mock_llm_regex_generation,
    )
    print(f"✓ Saved to {result.output_path}")

    # Verification: Check that all expected values are present
    print("\n=== Verification ===\n")
    nb = nbformat.read(result.output_path, as_version=4)

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
        raise AssertionError(f"Missing expected values: {missing}")

    print(f"✓ All {len(found_values)}/{len(expected_values)} expected values found in notebook")

    # Count markers that are present (markers are supposed to be there with values)
    markers_present = sum(
        1 for marker in [
            "##AGENT:name##",
            "##AGENT:inn_client##",
            "##AGENT:date_filter##",
            "##AGENT:date_filter2##",
            "##AGENT:lst_sbersov##",
            "##AGENT:list_words##",
            "##AGENT:regions_filter##",
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
    assert True


if __name__ == "__main__":
    path = Path("output/smoke_fixture")
    path.mkdir(parents=True, exist_ok=True)
    test_smoke_integration(path)
    sys.exit(0)
