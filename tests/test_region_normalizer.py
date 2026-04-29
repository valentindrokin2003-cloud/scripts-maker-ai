from src.region_normalizer import normalize_region, normalize_regions, resolve_region_filters


def test_all_russia_indicator_returns_empty_list():
    assert normalize_regions(["РФ"]) == []
    assert normalize_regions(["Все регионы РФ"]) == []
    assert normalize_regions(["Вся Россия"]) == []
    assert resolve_region_filters(["По всей РФ"]).regions == []
    assert resolve_region_filters(["По всей РФ"]).f_ocrygs == []


def test_splits_and_normalizes_combined_regions():
    result = normalize_regions(["Санкт-Петербург и Ленинградская область"])
    assert result == ["Санкт-Петербург", "Ленинградская область"]


def test_city_with_modifier_merges_to_region_when_needed():
    assert normalize_regions(["Калининград и область"]) == ["Калининградская область"]


def test_unknown_region_is_preserved_trimmed():
    assert normalize_region("  Неизвестный регион  ") == "Неизвестный регион"


def test_resolves_district_abbreviation_to_f_ocryg():
    result = resolve_region_filters(["СФО", "ЦФО"])
    assert result.regions == []
    assert result.f_ocrygs == ["СФО", "ЦФО"]


def test_resolves_full_district_name_to_f_ocryg():
    result = resolve_region_filters(["Сибирский федеральный округ"])
    assert result.regions == []
    assert result.f_ocrygs == ["СФО"]


def test_resolves_city_to_region():
    result = resolve_region_filters(["Новосибирск", "Томск"])
    assert result.regions == ["Новосибирская область", "Томская область"]
    assert result.f_ocrygs == []


def test_supports_mixed_region_and_district_filters():
    result = resolve_region_filters(["Новосибирск", "Томская область", "ЦФО", "Сибирский федеральный округ"])
    assert result.regions == ["Новосибирская область", "Томская область"]
    assert result.f_ocrygs == ["ЦФО", "СФО"]
