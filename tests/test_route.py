from irail.commands.cmd_route import verify_date, verify_time

def test_time_verification():
    valid_times = ["0000",
                   "0100",
                   "0110",
                   "2359"]
    invalid_times = ["000",
                     "159",
                     "2536",
                     "2396"]
    for item in valid_times:
        assert verify_time(item) is True

    for item in invalid_times:
        assert verify_time(item) is False