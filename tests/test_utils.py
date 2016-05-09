from irail.commands.utils import parse_vehicle_type, timestamp_to_human_readable_time
import pytest


def test_parse_vehicle():
    valid_test_cases = [
        ("BE.NMBS.IC545", "IC", "IC545"), 
        ("BE.NMBS.S4002", "S", "S4002"),
        ("BE.NMBS.L20", "L", "L20"),
        ("IC545", "IC", "IC545")]
    invalid_test_cases = [
    "",
    "IC",
    ]
    for test_case, train_type, full_train_type in valid_test_cases:
        assert parse_vehicle_type(test_case, include_number=False) == train_type
        assert parse_vehicle_type(test_case, include_number=True) == full_train_type
    for test_case in invalid_test_cases:
        with pytest.raises(ValueError):
            parse_vehicle_type(test_case)


def test_timestamp_to_human_readable_time():
    valid_test_cases = [("1462782390", "10:26", "10:26 (09/05/2016)")]
    invalid_test_cases = ["146278239", "1462782390a"]
    for test_case, hour_only, hour_and_date in valid_test_cases:
        assert timestamp_to_human_readable_time(test_case) == hour_only
        assert timestamp_to_human_readable_time(test_case, include_date=True) == hour_and_date
    for test_case in invalid_test_cases:
        with pytest.raises(ValueError):
            timestamp_to_human_readable_time(test_case)
