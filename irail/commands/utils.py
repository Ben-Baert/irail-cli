import requests
import pytz
from datetime import datetime
import click
import re


def api_request(feature, **input_params):
    headers = {'Content-type': 'application/json',
               'Accept': 'text/plain'}

    params = {"fast": "true",
              "format": "json",
              "from": input_params.get("from_station", None)}  # hack to get around from
    params.update(input_params)

    if feature == "station":
        url = "https://irail.be/stations/NMBS"
    else:
        url = "http://api.irail.be/{}/".format(feature)
    try:
        r = requests.get(url, params=params, headers=headers)
    except requests.exceptions.ConnectionError:

        try:
            requests.get('http://8.8.8.8/', timeout=1)
        except requests.exceptions.ConnectionError:
            click.echo("Your internet connection doesn't seem to be working.")
            raise SystemExit(1)
        else:
            click.echo("The iRail API doesn't seem to be working.")
            raise SystemExit(1)
    try:
        json_data = r.json()
    except ValueError:
        print(r.url)
        click.echo("The api doesn't seem to be working properly.")
        raise SystemExit(1)
    if "error" in json_data:
        click.echo("The api works, but sent a {} error code: {}".format(json_data["error"], json_data["message"]))
        raise SystemExit(1)
    return json_data


def station_request(station_name):
    return api_request("station", q=station_name)


def liveboard_request(station_name):
    return api_request("liveboard", station=station_name)


def vehicle_request(vehicle_id):
    return api_request("vehicle", id=vehicle_id)  # ["stops"]["stop"]


def route_request(from_station, to_station, date=None, time=None, time_selection="depart"):
    r = api_request("connections", from_station=from_station, to=to_station,
                       date=date, time=time, timeSel=time_selection)
    try:
        return r["connection"]
    except KeyError:
        raise NoConnectionsFound


def get_platform(connection):
    return human_readable_platform_from_platforminfo(connection["platforminfo"]["name"],
                          connection["platforminfo"]["normal"])

def get_station_from_user_input_name_from_connection(connection):
    return connection["stationinfo"]["standardname"]


def get_time_from_connection(connection):
    return timestamp_to_human_readable_time(connection["time"])


def get_arrival_time_from_via(via):
    return timestamp_to_human_readable_time(via["arrival"]["time"])


def get_arrival_platform_from_via(via):
    return get_platform(via["arrival"])


def get_departure_time_from_via(via):
    return timestamp_to_human_readable_time(via["departure"]["time"])


def get_departure_platform_from_via(via):
    return get_platform(via["departure"])


def get_human_readable_vehicle_from_connection(connection, include_number=False):
    return parse_vehicle_type(connection["vehicle"], include_number)


def timestamp_to_human_readable_time(timestamp, include_date=False):
    """
    Takes a timestamp, returns
    a human-readable (HH:MM)
    time string.
    """
    if not (len(timestamp) == 10 and all(c.isdigit() for c in timestamp)):
        raise ValueError("Timestamp {} is invalid and cannot be converted".format(timestamp))
    timezone = pytz.timezone('Europe/Brussels')
    return (datetime.fromtimestamp(int(timestamp), timezone)
                    .strftime("%H:%M (%d/%m/%Y)" if include_date else "%H:%M"))


def human_readable_platform_from_platforminfo(platform, platform_changed):
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


def parse_vehicle_type(vehicle, include_number=False):
    """
    Takes a vehicle string (BE.NMBS.IC504)
    and returns a human-readable
    version of its type (e.g. IC, L)
    """
    matches = re.match(r'(?:BE.NMBS.)?([A-Z]{1,3})(\d{1,4})', vehicle)
    try:
        train_type = matches.group(1)
    except AttributeError:
        raise ValueError("{} is not a valid vehicle".format(vehicle))
    train_number = matches.group(2)
    return train_type + (train_number if include_number else "")


def parse_direction(direction):
    return direction.ljust(40)


def safe_trains_extract(irail_json_object):
    try:
        return irail_json_object["departures"]["departure"]
    except KeyError:
        click.echo("No trains!")
        return []


def get_station_from_user_input(suggestion):
    """
    Takes a potential train station
    (e.g. Gent) and returns possibilities.
    User can then choose the exact train
    station (e.g. Gent-Sint-Pieters)
    from these possibilities.
    
    Example:
    bash-4.3$ irail liveboard gent
    0: Gent-Sint-Pieters
    1: Gent-Dampoort
    2: Gentbrugge
    Which station do you mean by gent?: 0
    """
    
    def try_station_index():
        station_index = click.prompt("Which station do you mean by {0}?".format(suggestion), type=int)
        try:
            return suggestions[station_index]["name"]
        except IndexError:
            click.echo("The station with #{} is not in the list. Please provide a valid index.".format(station_index))
            return try_station_index()

    json_data = station_request(suggestion)

    suggestions = json_data["@graph"]

    if len(suggestions) == 1:
        station_index = 0

    elif len(suggestions) == 0:
        click.echo("No station like {0} found.".format(suggestion))
        raise SystemExit(1)
    else:
        for index, station in enumerate(suggestions):
            click.echo(str(index) + ": " + station["name"])
        return try_station_index()


def get_human_readable_delay_from_connection(connection):
    return human_readable_delay_from_delay_string(connection["delay"])


def human_readable_delay_from_delay_string(delay_str):
    if delay_str == "0":
        return False, "   "
    elif delay_str == "cancel":
        return True, 0
    else:
        delay = int(delay_str) // 60
        text = ("+" + str(delay)).ljust(3)
        return False, click.style(text, fg="red")
