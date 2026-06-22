from app.features.snapshots import parse_stat_value


def test_parse_stat_value_handles_numbers_and_percentages() -> None:
    assert parse_stat_value(7) == 7.0
    assert parse_stat_value("1,234") == 1234.0
    assert parse_stat_value("73%") == 0.73
    assert parse_stat_value(None) is None
    assert parse_stat_value("n/a") is None
