from freezegun import freeze_time
from src.date_resolver import resolve_dates


@freeze_time("2026-03-17")
def test_last_6_months():
    start, end = resolve_dates("last_N_months:6")
    assert end == "2026-03-17"
    assert start == "2025-09-17"


@freeze_time("2026-03-17")
def test_last_12_months():
    start, end = resolve_dates("last_N_months:12")
    assert end == "2026-03-17"
    assert start == "2025-03-17"


@freeze_time("2026-03-17")
def test_last_3_months():
    start, end = resolve_dates("last_N_months:3")
    assert end == "2026-03-17"
    assert start == "2025-12-17"


def test_fixed_range():
    start, end = resolve_dates("range:2025-01-01:2025-12-31")
    assert start == "2025-01-01"
    assert end == "2025-12-31"


@freeze_time("2026-03-17")
def test_unknown_format_falls_back_to_6_months(capsys):
    start, end = resolve_dates("непонятный формат")
    out = capsys.readouterr().out
    assert "Warning" in out
    assert end == "2026-03-17"
    assert start == "2025-09-17"
