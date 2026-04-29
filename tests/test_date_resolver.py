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
def test_unknown_format_falls_back_to_6_months(caplog):
    start, end = resolve_dates("непонятный формат")
    assert "unrecognised analysis_period" in caplog.text
    assert end == "2026-03-17"
    assert start == "2025-09-17"


@freeze_time("2026-03-17")
def test_malformed_last_n_months_falls_back(caplog):
    start, end = resolve_dates("last_N_months:not-a-number")
    assert "unrecognised analysis_period" in caplog.text
    assert end == "2026-03-17"
    assert start == "2025-09-17"


@freeze_time("2026-03-17")
def test_non_positive_last_n_months_falls_back(caplog):
    start, end = resolve_dates("last_N_months:0")
    assert "months must be positive" in caplog.text
    assert end == "2026-03-17"
    assert start == "2025-09-17"


@freeze_time("2026-03-17")
def test_malformed_range_falls_back(caplog):
    start, end = resolve_dates("range:2025-01-01")
    assert "invalid range" in caplog.text
    assert end == "2026-03-17"
    assert start == "2025-09-17"


@freeze_time("2026-03-17")
def test_reversed_range_falls_back(caplog):
    start, end = resolve_dates("range:2025-12-31:2025-01-01")
    assert "range start is after end" in caplog.text
    assert end == "2026-03-17"
    assert start == "2025-09-17"
