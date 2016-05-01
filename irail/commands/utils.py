import requests
from datetime import datetime
import json
import click


"""
Utilities used in at least 2 of the 3
features go here.
"""


def get_station_name(connection):
    return connection["stationinfo"]["standardname"]


def get_time(connection):
    return parse_time(connection["time"])


def get_platform(connection):
    return parse_platform(connection["platforminfo"]["name"],
                          connection["platforminfo"]["normal"])


def get_arrival_time(via):
    return parse_time(via["arrival"]["time"])


def get_arrival_platform(via):
    return get_platform(via["arrival"])


def get_departure_time(via):
    return parse_time(via["departure"]["time"])


def get_departure_platform(via):
    return get_platform(via["departure"])


def get_vehicle(connection):
    return parse_vehicle_type(connection["vehicle"])


def parse_time(timestamp, include_date=False):
    """
    Takes a timestamp, returns
    a human-readable (HH:MM)
    time string.
    """
    return datetime.fromtimestamp(int(timestamp)).strftime("%H:%M (%d/%m/%Y)" if include_date else "%H:%M")


def parse_platform(platform, platform_changed):
    """
    Apply style to platform string.
    If platform is normal, simply return platform.
    If platform has been changed, apply 'reverse' style.
    """
    platform_changed = platform_changed != "1"
    platform_message = " " * (3 - len(platform))
    if not platform_changed:
        platform_message += platform
    else:
        platform_message += click.style(platform, reverse=True)
    return platform_message


def get_styled_platform(platform, platform_changed):
    pass

def parse_vehicle_type(vehicle):
    """
    Takes a vehicle string (BE.NMBS.IC504)
    and returns a human-readable
    version of its type (e.g. IC, L)
    """
    return (''.join(x for x in vehicle[8:10]
                    if x in "PLICS")
              .ljust(2))


def parse_direction(direction):
    return direction.ljust(40)


def safe_trains_extract(irail_json_object):
    try:
        return irail_json_object["departures"]["departure"]
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
    try:
        json_data = (requests.get(
                        "https://irail.be/stations/NMBS/",
                        {"q": suggestion},
                        headers=headers)
                        .json())
    except ValueError:
        click.echo("The api doesn't seem to be working properly.")
        raise SystemExit(0)
    except requests.exceptions.ConnectionError:
        try:
            requests.get('http://8.8.8.8/', timeout=1)
        except requests.exceptions.ConnectionError:
            click.echo("Your internet connection doesn't seem to be working.")
            raise SystemExit(0)
        else:
            click.echo("The iRail API doesn't seem to be working.")
            raise SystemExit(0)
    suggestions = json_data["@graph"]

    if len(suggestions) == 1:
        station_index = 0

    elif len(suggestions) == 0:
        click.echo("No station like {0} found.".format(suggestion))
        raise SystemExit(0)
    else:
        for index, station in enumerate(suggestions):
            click.echo(str(index) + ": " + station["name"])
        station_index = click.prompt("Which station do you mean by {0}?".format(suggestion), type=int)

    return suggestions[station_index]["name"]


def get_delay(connection):
    return parse_delay(connection["delay"])


def parse_delay(delay_str):
    if delay_str == "0":
        return False, "   "
    elif delay_str == "cancel":
        return True, 0
    else:
        delay = int(delay_str) // 60
        text = ("+" + str(delay)).ljust(3)
        return False, click.style(text, fg="red")
