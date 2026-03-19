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
import logging
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI
import httpx

# Configure logging
log_filename = f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"=== Agent started, logs will be saved to {log_filename} ===")

# Load environment variables from .env file
load_dotenv()

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
    patterns_repr = "[\n" + "".join(f'    r"{p}",\n' for p in list_words) + "]"
    r["##AGENT:list_words##"] = f"# ##AGENT:list_words##\nlist_words = {patterns_repr}"

    # 7. regions_filter - Region distribution cell
    r["##AGENT:regions_filter##"] = f"# ##AGENT:regions_filter##\n# Распределение по регионам\nintegrum = spark.read.table(ml360_folder.format('u_sparkinterfax_integrum'))\\\n                    .select('inn', 'okato_cd')\\\n                    .withColumn('okato', F.col('okato_cd')[0:2])\n        \n# okato = spark.read.parquet('okato').withColumnRenamed('okato_cd', 'okato')  \n\ninn_wth_regions = integrum.join(F.broadcast(spark.table(\"arnsdpsbx_t_team_monetization_products.ens_dict_cc_region_okato\")), on = 'okato', how = 'inner')\n\n\nregions = {brief.regions!r}\n\nif len(regions) > 0:\n    inn_wth_regions = inn_wth_regions.filter(F.col('region').isin(regions))"

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

    logger.info(f"Arguments: brief={args.brief}, output={args.output}")

    if not os.path.exists(args.brief):
        logger.error(f"Brief file not found: {args.brief}")
        print(f"Error: brief file not found: {args.brief}")
        sys.exit(1)

    os.makedirs(args.output, exist_ok=True)

    # Initialize DeepSeek client
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        logger.error("DEEPSEEK_API_KEY not set in .env file")
        print("Error: DEEPSEEK_API_KEY not set in .env file")
        sys.exit(1)

    logger.info("DEEPSEEK_API_KEY found in environment")
    logger.info(f"API Key length: {len(api_key)} chars")

    # Test API connectivity before starting main work
    logger.info("=" * 60)
    logger.info("Testing API connectivity...")
    logger.info("=" * 60)

    # Create httpx client without proxy settings from environment
    http_client = httpx.Client(trust_env=False)

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
        http_client=http_client
    )
    logger.info("✓ OpenAI client initialized for DeepSeek API")
    logger.info(f"  Base URL: https://api.deepseek.com")
    logger.info(f"  Model: deepseek-chat")

    # Try a quick test call
    try:
        logger.info("Attempting quick API test call (testing connection)...")
        test_response = client.chat.completions.create(
            model="deepseek-chat",
            max_tokens=100,
            timeout=30,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say OK"},
            ],
        )
        logger.info("✓ API test call successful - API is reachable")
        logger.info(f"  Response: {test_response.choices[0].message.content[:50]}")
    except Exception as e:
        logger.error(f"✗ API test call failed: {type(e).__name__}: {e}")
        logger.error(f"  The API might be unreachable. Check:")
        logger.error(f"  1. Internet connection")
        logger.error(f"  2. API endpoint (https://api.deepseek.com)")
        logger.error(f"  3. Firewall/proxy settings")
        logger.error(f"  4. API key validity")
        logger.warning("Continuing anyway, but main API calls may also fail...")

    logger.info("=" * 60)

    print(f"[1/6] Reading Excel brief: {args.brief}")
    logger.info(f"[1/6] Reading Excel brief: {args.brief}")
    excel_text = parse_excel_to_text(args.brief)
    logger.info(f"[1/6] Excel text extracted: {len(excel_text)} chars")

    print("[2/6] Extracting fields (DeepSeek API call 1)...")
    logger.info("[2/6] Starting brief extraction (API call 1)")
    try:
        brief = extract_brief(excel_text, client)
    except BriefExtractionError as e:
        logger.error(f"[2/6] Brief extraction failed: {e}")
        print(f"Error: {e}")
        sys.exit(1)
    logger.info(f"[2/6] Brief extraction succeeded")
    print(f"      → name: {brief.name}")

    print("[3/6] Resolving dates...")
    logger.info(f"[3/6] Resolving dates from period: {brief.analysis_period}")
    start_date, end_date = resolve_dates(brief.analysis_period)
    logger.info(f"[3/6] Dates resolved: {start_date} — {end_date}")
    print(f"      → {start_date} — {end_date}")

    print("[4/6] Matching words from dictionary...")
    logger.info(f"[4/6] Matching {len(brief.product_words)} product words from dictionary")
    lst_sbersov = match_words(brief.product_words, DICT_PATH)
    logger.info(f"[4/6] Word matching complete: {len(lst_sbersov)} matches")
    print(f"      → {len(lst_sbersov)} words matched: {lst_sbersov}")

    print("[5/6] Generating regex patterns (DeepSeek API call 2)...")
    logger.info("[5/6] Starting regex generation (API call 2)")
    list_words = generate_regex(brief.product_words, client)
    logger.info(f"[5/6] Regex generation complete: {len(list_words)} patterns")
    print(f"      → {len(list_words)} patterns generated")

    print("[6/6] Filling notebook template...")
    logger.info(f"[6/6] Loading template from {TEMPLATE_PATH}")
    nb = load_template(TEMPLATE_PATH)
    logger.info(f"[6/6] Building replacements and filling notebook")
    replacements = build_replacements(brief, start_date, end_date, lst_sbersov, list_words)
    fill_notebook(nb, replacements)

    output_path = os.path.join(args.output, f"{brief.name_safe}_script.ipynb")
    save_notebook(nb, output_path)
    logger.info(f"[6/6] Notebook saved to {output_path}")
    print(f"\nDone! Output: {output_path}")


if __name__ == "__main__":
    main()
