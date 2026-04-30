"""Run with: pytest tests/"""
from processing.floor_parser import parse_floor, floor_band


def test_simple_floor():
    fi = parse_floor("15/F")
    assert fi.floor_low == 15 and fi.floor_high == 15
    assert fi.is_whole_floor


def test_floor_range():
    fi = parse_floor("8-10/F")
    assert fi.floor_low == 8 and fi.floor_high == 10
    assert fi.is_whole_floor


def test_floor_range_with_dash():
    fi = parse_floor("8/F – 10/F")
    assert fi.floor_low == 8 and fi.floor_high == 10


def test_high_zone():
    fi = parse_floor("High Zone 35/F")
    assert fi.floor_zone == "High"
    assert fi.floor_low == 35


def test_unit_means_partial():
    fi = parse_floor("15/F Unit A")
    assert fi.unit == "A"
    assert fi.is_partial_floor
    assert not fi.is_whole_floor


def test_whole_floor_keyword():
    fi = parse_floor("Whole 12/F")
    assert fi.is_whole_floor
    assert fi.floor_low == 12


def test_ground_floor():
    fi = parse_floor("G/F")
    assert fi.floor_low == 0


def test_basement():
    fi = parse_floor("B1/F")
    assert fi.floor_low == -1


def test_chinese_floor():
    fi = parse_floor("高層 35/F")
    assert fi.floor_zone == "High"


def test_floor_band():
    assert floor_band(5, 5) == "Low (≤10F)"
    assert floor_band(20, 22) == "Mid (11–30F)"
    assert floor_band(45, 50) == "High (31–60F)"
    assert floor_band(85, 85) == "Super-high (>60F)"
    assert floor_band(None, None) == "Unknown"


def test_empty():
    fi = parse_floor("")
    assert fi.floor_low is None
    assert not fi.is_whole_floor
