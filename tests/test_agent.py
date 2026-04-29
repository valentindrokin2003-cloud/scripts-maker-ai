from src.models import BriefData
from src.notebook_replacements import build_replacements


def _brief(**kwargs):
    defaults = dict(
        name="ООО Фреш",
        inn_client=["5009138436"],
        analysis_period="last_N_months:6",
    )
    defaults.update(kwargs)
    return BriefData(**defaults)


def test_all_11_markers_present():
    bd = _brief()
    r = build_replacements(bd, "2025-09-17", "2026-03-17", [], [])
    expected_markers = [
        "##AGENT:name##", "##AGENT:inn_client##", "##AGENT:date_filter##",
        "##AGENT:date_filter2##", "##AGENT:lst_sbersov##", "##AGENT:list_words##",
        "##AGENT:regions_filter##", "##AGENT:okved_list##", "##AGENT:exclusions##",
        "##AGENT:revenue##", "##AGENT:trans_thresholds##",
    ]
    for marker in expected_markers:
        assert marker in r, f"Missing marker: {marker}"


def test_name_inserted():
    bd = _brief(name="ООО Тест")
    r = build_replacements(bd, "2025-09-17", "2026-03-17", [], [])
    assert "name = 'ООО Тест'" in r["##AGENT:name##"]


def test_dates_inserted():
    bd = _brief()
    r = build_replacements(bd, "2025-09-17", "2026-03-17", [], [])
    assert "'2025-09-17'" in r["##AGENT:date_filter##"]
    assert "'2026-03-17'" in r["##AGENT:date_filter##"]
    assert "'2025-09-17'" in r["##AGENT:date_filter2##"]


def test_revenue_no_max():
    bd = _brief(revenue_min=1_000_000, revenue_max=None)
    r = build_replacements(bd, "2025-09-17", "2026-03-17", [], [])
    assert "end_rev" not in r["##AGENT:revenue##"]
    assert "start_rev = 1_000_000" in r["##AGENT:revenue##"]


def test_revenue_with_max():
    bd = _brief(revenue_min=100_000_000, revenue_max=500_000_000)
    r = build_replacements(bd, "2025-09-17", "2026-03-17", [], [])
    assert "end_rev = 500_000_000" in r["##AGENT:revenue##"]
    assert "end_rev" in r["##AGENT:revenue##"]


def test_okved_empty_no_filter():
    bd = _brief(okved_list=[])
    r = build_replacements(bd, "2025-09-17", "2026-03-17", [], [])
    assert ".isin(" not in r["##AGENT:okved_list##"]


def test_okved_nonempty_adds_filter():
    bd = _brief(okved_list=["46.11", "46.12"])
    r = build_replacements(bd, "2025-09-17", "2026-03-17", [], [])
    assert ".isin(okved_list)" in r["##AGENT:okved_list##"]


def test_exclusions_empty():
    bd = _brief(exclusions=[])
    r = build_replacements(bd, "2025-09-17", "2026-03-17", [], [])
    assert "data=[]" in r["##AGENT:exclusions##"]


def test_exclusions_nonempty():
    bd = _brief(exclusions=["7722406860"])
    r = build_replacements(bd, "2025-09-17", "2026-03-17", [], [])
    assert "7722406860" in r["##AGENT:exclusions##"]


def test_list_words_empty_produces_valid_python():
    bd = _brief()
    r = build_replacements(bd, "2025-09-17", "2026-03-17", [], [])
    src = r["##AGENT:list_words##"]
    ns = {}
    exec(src.replace("# ##AGENT:list_words##\n", ""), ns)
    assert ns["list_words"] == []


def test_list_words_populated():
    patterns = [r'\bфасадн\w{0,3}\b']
    bd = _brief()
    r = build_replacements(bd, "2025-09-17", "2026-03-17", [], patterns)
    output = r["##AGENT:list_words##"]
    assert r"r'\bфасадн\w{0,3}\b'" in output
    assert r"'\\bфасадн\\w{0,3}\\b'" not in output
    ns = {}
    exec(output.replace("# ##AGENT:list_words##\n", ""), ns)
    assert ns["list_words"] == patterns


def test_list_words_with_quotes_produces_valid_python():
    patterns = [r'\bbrand "x"\b']
    bd = _brief()
    r = build_replacements(bd, "2025-09-17", "2026-03-17", [], patterns)
    src = r["##AGENT:list_words##"]
    ns = {}
    exec(src.replace("# ##AGENT:list_words##\n", ""), ns)
    assert ns["list_words"] == patterns


def test_regions_filter_supports_mixed_regions_and_federal_districts():
    bd = _brief(regions=["Новосибирская область"], f_ocrygs=["СФО", "ЦФО"])
    r = build_replacements(bd, "2025-09-17", "2026-03-17", [], [])
    output = r["##AGENT:regions_filter##"]
    assert "regions = ['Новосибирская область']" in output
    assert "f_ocrygs = ['СФО', 'ЦФО']" in output
    assert "F.col('region').isin(regions) | F.col('f_ocryg').isin(f_ocrygs)" in output
