"""
Utilities used in at least 2 of the 3
features go here.
"""

def parse_time(timestamp):
    """
    Takes a timestamp, returns
    a human-readable (HH:MM)
    time string.
    """
    return datetime.fromtimestamp(int(timestamp)).strftime("%H:%M")


def parse_platform(platform, platform_changed):
    """
    Apply style to platform string.
    If platform is normal, simply return platform.
    If platform has been changed, apply 'reverse' style.
    """
    platform_changed = platform_changed != "1"
    platform_message = " " + platform.rjust(2)
    if platform_changed:
        return click.style(platform_message, reverse=True)
    return platform_message

def parse_vehicle(vehicle):
    """
    Takes a vehicle string (BE.NMBS.IC.)
    and returns a human-readable
    version (e.g. IC, L)
    """
    return (''.join(x for x in vehicle[8:10]
                    if x in "PLIC")
              .ljust(2))


def parse_direction(direction):
    return direction.ljust(40)


def safe_trains_extract(irail_json_object):
    try:
        return json_object["departures"]["departure"]
    except KeyError:
        click.echo("No trains!")
        return []


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
                    {"q": suggestion},
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


def parse_delay(delay_str):
    if delay_str == "0":
        return False, "   "
    elif delay_str == "cancel":
        return True, 0
    else:
        delay = int(delay_str) // 60
        text = ("+" + str(delay)).ljust(3)
        return False, click.style(text, fg="red")
