#!/usr/bin/env python3
"""
B2B Script Agent — generates a populated Jupyter notebook from an Excel brief.

Usage:
    python agent.py --brief "data/ТЗ_Fresh.xlsx"
    python agent.py --brief "data/ТЗ_Fresh.xlsx" --output "my_output/"
"""
import argparse
import os
import sys

import anthropic

from src.brief_extractor import extract_brief, BriefExtractionError
from src.date_resolver import resolve_dates
from src.excel_parser import parse_excel_to_text
from src.notebook_filler import fill_notebook, load_template, save_notebook
from src.regex_generator import generate_regex
from src.words_matcher import match_words

TEMPLATE_PATH = "templates/b2b_template.ipynb"
DICT_PATH = "data/words_ok_groups_v2.xlsx"


def build_replacements(brief, start_date: str, end_date: str,
                        lst_sbersov: list, list_words: list) -> dict:
    r = {}

    # 1. name
    r["##AGENT:name##"] = f"# ##AGENT:name##\nname = {brief.name!r}"

    # 2. inn_client
    r["##AGENT:inn_client##"] = (
        f"# ##AGENT:inn_client##\ninn_client = {brief.inn_client!r}"
    )

    # 3. date_filter
    r["##AGENT:date_filter##"] = (
        f"# ##AGENT:date_filter##\n"
        f"words_finadv = words_finadv[\n"
        f"    (~words_finadv['c_nazn'].isNull())\n"
        f"    & (words_finadv['short_dt'] >= {start_date!r})\n"
        f"    & (words_finadv['short_dt'] <= {end_date!r})\n"
        f"]"
    )

    # 4. date_filter2
    r["##AGENT:date_filter2##"] = (
        f"# ##AGENT:date_filter2##\n"
        f"words_finadv_upd_ = words_finadv_upd[\n"
        f"    (words_finadv_upd['short_dt'] >= {start_date!r})\n"
        f"    & (words_finadv_upd['short_dt'] <= {end_date!r})\n"
        f"]"
    )

    # 5. lst_sbersov
    r["##AGENT:lst_sbersov##"] = (
        f"# ##AGENT:lst_sbersov##\n"
        f"lst_sbersov = {lst_sbersov!r}\n\n"
        f"df_sbersov_spark = spark.createDataFrame(pd.DataFrame(lst_sbersov, columns=['word']))"
    )

    # 6. list_words
    patterns_repr = "[\n" + "".join(f"    {p!r},\n" for p in list_words) + "]"
    r["##AGENT:list_words##"] = f"# ##AGENT:list_words##\nlist_words = {patterns_repr}"

    # 7. regions
    r["##AGENT:regions##"] = f"# ##AGENT:regions##\nregions = {brief.regions!r}"

    # 8. okved_list
    if brief.okved_list:
        okved_block = (
            f"# ##AGENT:okved_list##\n"
            f"okved_list = {brief.okved_list!r}\n"
            f"okved_ = okved_part\\\n"
            f"    .filter(F.col('okved_original_version') == 2)\\\n"
            f"    .filter(F.col('okved').isin(okved_list))\\\n"
            f"    .drop_duplicates(subset=['inn'])\\\n"
            f"    .select('inn', 'okved')"
        )
    else:
        okved_block = (
            f"# ##AGENT:okved_list##\n"
            f"okved_list = []\n"
            f"okved_ = okved_part\\\n"
            f"    .filter(F.col('okved_original_version') == 2)\\\n"
            f"    .drop_duplicates(subset=['inn'])\\\n"
            f"    .select('inn', 'okved')"
        )
    r["##AGENT:okved_list##"] = okved_block

    # 9. exclusions
    if brief.exclusions:
        r["##AGENT:exclusions##"] = (
            f"# ##AGENT:exclusions##\n"
            f"df_exclusions = pd.DataFrame(data={brief.exclusions!r}, columns=['inn'])"
        )
    else:
        r["##AGENT:exclusions##"] = (
            f"# ##AGENT:exclusions##\n"
            f"df_exclusions = pd.DataFrame(data=[], columns=['inn'])"
        )

    # 10. revenue
    if brief.revenue_max is not None:
        rev_block = (
            f"# ##AGENT:revenue##\n"
            f"start_rev = {brief.revenue_min:_}\n"
            f"end_rev = {brief.revenue_max:_}\n"
            f"revenue_filtered = revenue_2022_2023.filter(\n"
            f"    (F.col('revenue') >= start_rev) & (F.col('revenue') <= end_rev)\n"
            f")"
        )
    else:
        rev_block = (
            f"# ##AGENT:revenue##\n"
            f"start_rev = {brief.revenue_min:_}\n"
            f"revenue_filtered = revenue_2022_2023.filter(F.col('revenue') >= start_rev)"
        )
    r["##AGENT:revenue##"] = rev_block

    # 11. trans_thresholds
    r["##AGENT:trans_thresholds##"] = (
        f"# ##AGENT:trans_thresholds##\n"
        f"trans_sum_ust_down = {brief.trans_sum_min:_}\n"
        f"trans_cnt_ust_down = {brief.trans_cnt_min}"
    )

    return r


def main():
    parser = argparse.ArgumentParser(description="B2B Script Agent")
    parser.add_argument("--brief", required=True, help="Path to Excel brief (.xlsx)")
    parser.add_argument("--output", default="output", help="Output directory (default: output/)")
    args = parser.parse_args()

    if not os.path.exists(args.brief):
        print(f"Error: brief file not found: {args.brief}")
        sys.exit(1)

    os.makedirs(args.output, exist_ok=True)
    client = anthropic.Anthropic()

    print(f"[1/6] Reading Excel brief: {args.brief}")
    excel_text = parse_excel_to_text(args.brief)

    print("[2/6] Extracting fields (Claude call 1)...")
    try:
        brief = extract_brief(excel_text, client)
    except BriefExtractionError as e:
        print(f"Error: {e}")
        sys.exit(1)
    print(f"      → name: {brief.name}")

    print("[3/6] Resolving dates...")
    start_date, end_date = resolve_dates(brief.analysis_period)
    print(f"      → {start_date} — {end_date}")

    print("[4/6] Matching words from dictionary...")
    lst_sbersov = match_words(brief.product_words, DICT_PATH)
    print(f"      → {len(lst_sbersov)} words matched: {lst_sbersov}")

    print("[5/6] Generating regex patterns (Claude call 2)...")
    list_words = generate_regex(brief.product_words, client)
    print(f"      → {len(list_words)} patterns generated")

    print("[6/6] Filling notebook template...")
    nb = load_template(TEMPLATE_PATH)
    replacements = build_replacements(brief, start_date, end_date, lst_sbersov, list_words)
    fill_notebook(nb, replacements)

    output_path = os.path.join(args.output, f"{brief.name_safe}_script.ipynb")
    save_notebook(nb, output_path)
    print(f"\nDone! Output: {output_path}")


if __name__ == "__main__":
    main()
