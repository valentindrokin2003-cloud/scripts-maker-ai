import logging
import os
import threading
from dataclasses import dataclass
from typing import Any, Callable

from src.brief_extractor import BriefExtractionError, extract_brief
from src.brief_review import review_brief
from src.date_resolver import resolve_dates
from src.excel_parser import parse_excel_to_text
from src.models import BriefData, BriefReview
from src.notebook_filler import fill_notebook, load_template, save_notebook
from src.notebook_replacements import build_replacements
from src.regex_generator import generate_regex
from src.settings import AgentSettings
from src.words_matcher import match_words

logger = logging.getLogger(__name__)

class PipelineCancelledError(Exception):
    pass


ProgressCallback = Callable[[str], None]
BriefExtractor = Callable[[str, Any, str], BriefData]
BriefReviewer = Callable[[str, BriefData], BriefReview]
RegexGenerator = Callable[[list[str], Any, str], list[str]]


@dataclass(frozen=True)
class PipelineResult:
    status: str
    brief: BriefData
    review: BriefReview | None
    start_date: str | None
    end_date: str | None
    lst_sbersov: list[str]
    list_words: list[str]
    output_path: str | None
    excel_text: str


def _notify(progress: ProgressCallback | None, message: str) -> None:
    if progress:
        progress(message)


def _check_cancel(cancel_event: threading.Event | None) -> None:
    if cancel_event and cancel_event.is_set():
        raise PipelineCancelledError("Pipeline cancelled by user")


def run_pipeline(
    brief_path: str,
    output_dir: str,
    settings: AgentSettings,
    client: Any,
    *,
    progress: ProgressCallback | None = None,
    brief_extractor: BriefExtractor = extract_brief,
    brief_reviewer: BriefReviewer = review_brief,
    regex_generator: RegexGenerator = generate_regex,
    cancel_event: threading.Event | None = None,
) -> PipelineResult:
    """Run the notebook generation workflow and stop early if the brief needs revision."""
    os.makedirs(output_dir, exist_ok=True)

    _notify(progress, f"[1/7] Reading Excel brief: {brief_path}")
    logger.info(f"[1/7] Reading Excel brief: {brief_path}")
    excel_text = parse_excel_to_text(brief_path)
    logger.info(f"[1/7] Excel text extracted: {len(excel_text)} chars")

    _check_cancel(cancel_event)

    _notify(progress, "[2/7] Extracting fields (DeepSeek API call 1)...")
    logger.info("[2/7] Starting brief extraction (API call 1)")
    try:
        brief = brief_extractor(excel_text, client, settings.llm_model)
    except BriefExtractionError:
        logger.exception("[2/7] Brief extraction failed")
        raise
    logger.info("[2/7] Brief extraction succeeded")
    _notify(progress, f"      -> name: {brief.name}")

    _check_cancel(cancel_event)

    _notify(progress, "[3/7] Reviewing brief quality...")
    logger.info("[3/7] Starting brief review")
    review = brief_reviewer(excel_text, brief)
    logger.info("[3/7] Brief review status: %s", review.status)
    if review.status == "needs_revision":
        issue_count = len(review.issues)
        _notify(progress, f"      -> brief requires revision: {issue_count} issues")
        return PipelineResult(
            status="needs_revision",
            brief=brief,
            review=review,
            start_date=None,
            end_date=None,
            lst_sbersov=[],
            list_words=[],
            output_path=None,
            excel_text=excel_text,
        )

    _check_cancel(cancel_event)

    _notify(progress, "[4/7] Resolving dates...")
    logger.info(f"[4/7] Resolving dates from period: {brief.analysis_period}")
    start_date, end_date = resolve_dates(brief.analysis_period)
    logger.info(f"[4/7] Dates resolved: {start_date} - {end_date}")
    _notify(progress, f"      -> {start_date} - {end_date}")

    _check_cancel(cancel_event)

    _notify(progress, "[5/7] Matching words from dictionary...")
    logger.info(f"[5/7] Matching {len(brief.product_words)} product words from dictionary")
    lst_sbersov = match_words(brief.product_words, settings.dict_path)
    logger.info(f"[5/7] Word matching complete: {len(lst_sbersov)} matches")
    _notify(progress, f"      -> {len(lst_sbersov)} words matched: {lst_sbersov}")

    _check_cancel(cancel_event)

    _notify(progress, "[6/7] Generating regex patterns (DeepSeek API call 2)...")
    logger.info("[6/7] Starting regex generation (API call 2)")
    logger.info(f"[6/7] Regex input words: {brief.product_words}")
    list_words = regex_generator(brief.product_words, client, settings.llm_model)
    logger.info(f"[6/7] Regex generation complete: {len(list_words)} patterns")
    _notify(progress, f"      -> {len(list_words)} patterns generated")

    _check_cancel(cancel_event)

    _notify(progress, "[7/7] Filling notebook template...")
    logger.info(f"[7/7] Loading template from {settings.template_path}")
    nb = load_template(settings.template_path)
    logger.info("[7/7] Building replacements and filling notebook")
    replacements = build_replacements(
        brief,
        start_date,
        end_date,
        lst_sbersov,
        list_words,
        blocks_dir=settings.notebook_blocks_dir,
    )
    fill_notebook(nb, replacements)

    output_path = os.path.join(output_dir, f"{brief.name_safe}_script.ipynb")
    save_notebook(nb, output_path)
    logger.info(f"[7/7] Notebook saved to {output_path}")

    return PipelineResult(
        status="completed",
        brief=brief,
        review=review,
        start_date=start_date,
        end_date=end_date,
        lst_sbersov=lst_sbersov,
        list_words=list_words,
        output_path=output_path,
        excel_text=excel_text,
    )
