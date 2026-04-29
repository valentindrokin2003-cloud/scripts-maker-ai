
from src.models import BriefData

def test_briefdata_required_fields():
    bd = BriefData(
        name="ООО Фреш",
        inn_client=["5009138436"],
        analysis_period="last_N_months:6",
    )
    assert bd.name == "ООО Фреш"
    assert bd.inn_client == ["5009138436"]

def test_briefdata_defaults():
    bd = BriefData(
        name="Test",
        inn_client=["1234567890"],
        analysis_period="last_N_months:6",
    )
    assert bd.product_words == []
    assert bd.regions == []
    assert bd.f_ocrygs == []
    assert bd.okved_list == []
    assert bd.okved_explanations == {}
    assert bd.exclusions == []
    assert bd.revenue_min == 100_000_000
    assert bd.revenue_max is None
    assert bd.trans_sum_min == 10_000_000
    assert bd.trans_cnt_min == 3

def test_briefdata_name_safe():
    bd = BriefData(name="ООО Фреш/2024", inn_client=[], analysis_period="x")
    assert bd.name_safe == "ООО_Фреш_2024"
