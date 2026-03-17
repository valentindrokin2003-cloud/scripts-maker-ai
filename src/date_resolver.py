from datetime import date
from dateutil.relativedelta import relativedelta
from typing import Tuple


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
            n = 6
        start = today - relativedelta(months=n)
        return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

    if analysis_period.startswith("range:"):
        parts = analysis_period.split(":")
        # format: range:YYYY-MM-DD:YYYY-MM-DD
        start_str = parts[1]
        end_str = parts[2]
        return start_str, end_str

    print(f"Warning: unrecognised analysis_period '{analysis_period}', defaulting to last 6 months.")
    start = today - relativedelta(months=6)
    return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
