from processing.cleaner import (
    normalize_district, normalize_building_name, normalize_grade,
)
from utils.helpers import parse_money_hkd, parse_area_sqft


def test_district_alias():
    assert normalize_district("TST") == "Tsim Sha Tsui"
    assert normalize_district("Causeway Bay") == "Causeway Bay"
    assert normalize_district("kt") == "Kwun Tong"


def test_district_in_address():
    assert normalize_district("88 Queensway, Admiralty") == "Admiralty"


def test_building_alias():
    assert normalize_building_name("ICC") == "International Commerce Centre"
    assert normalize_building_name("2IFC") == "Two IFC"


def test_grade():
    assert normalize_grade("Grade A") == "A"
    assert normalize_grade("B") == "B"
    assert normalize_grade(None) is None


def test_money_billions():
    assert parse_money_hkd("HK$1.2B") == 1.2e9
    assert parse_money_hkd("$850M") == 8.5e8
    assert parse_money_hkd("HKD 95,000,000") == 95_000_000


def test_area():
    assert parse_area_sqft("12,500 sq ft") == 12500
    assert round(parse_area_sqft("100 sqm")) == 1076       # 100 * 10.7639
