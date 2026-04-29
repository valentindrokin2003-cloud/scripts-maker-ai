import logging
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from typing import Tuple

logger = logging.getLogger(__name__)


def _fallback_last_6_months(today: date, reason: str) -> Tuple[str, str]:
    logger.warning(reason)
    start = today - relativedelta(months=6)
    return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")


def _is_iso_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def resolve_dates(analysis_period: str) -> Tuple[str, str]:
    """
    Parse a normalised period string and return (start_date, end_date) as YYYY-MM-DD strings.

    Supported forms:
      "last_N_months:N"         — last N months ending today
      "range:YYYY-MM-DD:YYYY-MM-DD" — fixed date range
      anything else             — falls back to last 6 months with a warning
    """
    today = date.today()

    if analysis_period.startswith("last_N_months:"):
        try:
            n = int(analysis_period.split(":")[1])
        except (IndexError, ValueError):
            return _fallback_last_6_months(
                today,
                f"unrecognised analysis_period '{analysis_period}', defaulting to last 6 months.",
            )
        if n <= 0:
            return _fallback_last_6_months(
                today,
                f"analysis_period months must be positive: '{analysis_period}', defaulting to last 6 months.",
            )
        start = today - relativedelta(months=n)
        return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

    if analysis_period.startswith("range:"):
        parts = analysis_period.split(":")
        if len(parts) != 3 or not _is_iso_date(parts[1]) or not _is_iso_date(parts[2]):
            return _fallback_last_6_months(
                today,
                f"invalid range analysis_period '{analysis_period}', defaulting to last 6 months.",
            )
        # format: range:YYYY-MM-DD:YYYY-MM-DD
        start_str = parts[1]
        end_str = parts[2]
        if start_str > end_str:
            return _fallback_last_6_months(
                today,
                f"range start is after end in analysis_period '{analysis_period}', defaulting to last 6 months.",
            )
        return start_str, end_str

    return _fallback_last_6_months(
        today,
        f"unrecognised analysis_period '{analysis_period}', defaulting to last 6 months.",
    )
