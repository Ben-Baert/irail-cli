def readable_time(timestamp):
    """
    Takes a timestamp, returns
    a human-readable (HH:MM)
    time string.
    """
    return datetime.fromtimestamp(int(timestamp)).strftime("%H:%M")


def readable_platform(train):
    """
    Extract platform from train object.
    Apply style to platform string.
    If platform is normal, simply return platform.
    If platform has been changed, apply 'reverse' style.
    """
    platform = train["platform"]
    platform_changed = train["platforminfo"]["normal"] != "1"
    platform_message = " " + platform.rjust(2)
    if platform_changed:
        return click.style(platform_message, reverse=True)
    return platform_message


def make_station_header(json_object,
                        direction_filter,
                        vehicle_filter):
    name = json_object["stationinfo"]["standardname"]
    station_time = parse_timestamp(json_object["timestamp"])
    msg = (name +
            (" (direction: " +
                (direction_filter or vehicle_filter) +
                ")") if direction_filter or vehicle_filter
            else "")
    click.secho(station_time +
                " " +
                str.center(msg, TERMINAL_WIDTH - 6),
                reverse=True)
    return name


def safe_trains_extract(irail_json_object):
    try:
        return json_object["departures"]["departure"]
    except KeyError:
        click.echo("No trains!")
        return []


def readable_vehicle(vehicle_id_string):
    """
    Takes a vehicle string (BE.NMBS.IC.)
    and returns a human-readable
    version (e.g. IC, L)
    """
    return (''.join(x for x in vehicle_id_string[8:10]
                    if x in "PLIC")
              .ljust(2))


def get_station(suggestion):
    """
    Takes a potential train station
    (e.g. Gent) and returns possibilities.
    User can then choose the exact train
    station (e.g. Gent-Sint-Pieters)
    from these possibilities.
    """
    headers = {'Content-type': 'application/json',
               'Accept': 'text/plain'}
    json_data = (requests.get(
                    "https://irail.be/stations/NMBS/",
                    {"q" : suggestion},
                    headers=headers)
                    .json())
    suggestions = json_data["@graph"]

    if len(suggestions) == 1:
        station_index = 0
            
    elif len(suggestions) == 0:
        click.echo(
            """
            No station like {0} found.
            Please verify that you have
            an existing train station in
            Belgium and try again.
            """.format(suggestion))
        raise SystemExit(0)
    else:
        for index, station in enumerate(suggestions):
            click.echo(str(index) + ": " + station["name"])
        station_index = click.prompt(
                            """
                            Which station do you mean by {0}?
                            """.format(suggestion),
                            type=int)

    return suggestions[station_index]["name"]


def readable_delay(delay_str):
    if delay_str == "0":
        return False, "   "
    elif delay_str == "cancel":
        return True, 0
    else:
        delay = int(delay_str) // 60
        text = ("+" + str(delay)).ljust(3)
        return False, click.style(text, fg="red")





def vehicle_filter_check(train, vehicle_filter):
    if vehicle_filter:
        vehicle_id = train["vehicle"]
        v = requests.get(
                "http://api.irail.be/vehicle/",
                params={
                    "fast": "true",
                    "format": "json",
                    "id" : vehicle_id}).json()
        stops = v["stops"]["stop"]
        current_station_passed = False
        for stop in stops:
            if stop["station"] == station_name:
                current_station_passed = True
            if current_station_passed and stop["station"].startswith(vehicle_filter):
                arrival_time = parse_timestamp(stop["time"])
                return True, arrival_time
        return False, None
    return True, None
