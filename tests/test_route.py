import random
from datetime import datetime
from irail.commands.cmd_route import verify_date, verify_time, duration_int_to_human_readable_duration


def test_time_verification():
    acceptable_hours = [str(x).zfill(2) for x in range(0, 24)]
    acceptable_minutes = [str(x).zfill(2) for x in range(0, 60)]
    valid_times = [random.choice(acceptable_hours) + random.choice(acceptable_minutes) for _ in range(10)]
    invalid_times = ["000",
                     "159",
                     "2536",
                     "2396"]
    for item in valid_times:
        assert verify_time(item) is True

    for item in invalid_times:
        assert verify_time(item) is False

def test_date_verification():
    acceptable_days = [str(x).zfill(2) for x in range(1, 32)]
    acceptable_months = [str(x).zfill(2) for x in range(1, 13)]
    acceptable_years = list(str(datetime.now().year % 100 - i) for i in (-1, 0, 1))
    for _ in range(100):
        test_case = (random.choice(acceptable_days) +
                     random.choice(acceptable_months) +
                     random.choice(acceptable_years))
        assert verify_date(test_case) is True

def test_duration_int_to_human_readable_duration():
    pass