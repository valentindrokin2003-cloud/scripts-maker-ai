#!/usr/bin/env python3
"""
B2B Script Agent — generates a populated Jupyter notebook from an Excel brief.

Usage:
    python agent.py --brief "data/ТЗ_Fresh.xlsx"
    python agent.py --brief "data/ТЗ_Fresh.xlsx" --output "my_output/"
"""
import argparse
from pathlib import Path
import os
import sys
import logging
from datetime import datetime

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

from src.brief_extractor import BriefExtractionError
from src.llm_client import check_client_connection, create_openai_client
from src.pipeline import run_pipeline
from src.settings import AgentSettings, DEFAULT_DICT_PATH, DEFAULT_TEMPLATE_PATH

TEMPLATE_PATH = DEFAULT_TEMPLATE_PATH
DICT_PATH = DEFAULT_DICT_PATH


def configure_logging(log_file: str | None = None) -> str:
    """Configure CLI logging and return the file used for detailed logs."""
    if log_file is None:
        log_dir = Path(os.getenv("LOG_DIR", "logs"))
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = str(log_dir / f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    else:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[file_handler, console_handler],
        force=True,
    )
    return log_file


def main():
    load_dotenv()
    settings = AgentSettings.from_env()

    parser = argparse.ArgumentParser(description="B2B Script Agent")
    parser.add_argument("--brief", required=True, help="Path to Excel brief (.xlsx)")
    parser.add_argument(
        "--output",
        default=settings.output_dir,
        help=f"Output directory (default: {settings.output_dir}/)",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Detailed log file path (default: logs/agent_YYYYmmdd_HHMMSS.log)",
    )
    parser.add_argument(
        "--skip-api-check",
        action="store_true",
        help="Skip the quick preflight API connectivity call.",
    )
    args = parser.parse_args()

    log_file = configure_logging(args.log_file)
    logger.info(f"Arguments: brief={args.brief}, output={args.output}")
    logger.info(f"Detailed log file: {log_file}")

    if not os.path.exists(args.brief):
        logger.error(f"Brief file not found: {args.brief}")
        print(f"Error: brief file not found: {args.brief}")
        sys.exit(1)

    # Initialize DeepSeek client
    if not settings.api_key:
        logger.error("DEEPSEEK_API_KEY not set in .env file")
        print("Error: DEEPSEEK_API_KEY not set in .env file")
        sys.exit(1)

    logger.info("DEEPSEEK_API_KEY found in environment")
    logger.info(f"API Key length: {len(settings.api_key)} chars")

    client = create_openai_client(settings)
    if not args.skip_api_check:
        check_client_connection(client, settings, logger)

    try:
        result = run_pipeline(args.brief, args.output, settings, client, progress=print)
    except BriefExtractionError as e:
        print(f"Error: {e}")
        sys.exit(1)

    if result.status == "needs_revision":
        print("\nБриф требует доработки. Генерация notebook остановлена.")
        if result.review:
            for index, issue in enumerate(result.review.issues, start=1):
                print(f"{index}. [{issue.severity}] {issue.title}")
                print(f"   {issue.detail}")
        sys.exit(2)

    print(f"\nDone! Output: {result.output_path}")


if __name__ == "__main__":
    main()
