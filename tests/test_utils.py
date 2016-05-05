from irail.commands.utils import parse_vehicle_type


def test_parse_vehicle():
    test_case = "BE.NMBS.IC545"
    assert parse_vehicle_type(test_case, include_number=False) == "IC"
    assert parse_vehicle_type(test_case, include_number=True) == "IC545"
