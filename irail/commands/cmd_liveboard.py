import click
import requests
from time import sleep
from irail.cli import pass_context
from irail.commands.utils import *


def get_direction(connection):
    return connection["stationinfo"]["name"]

def get_platform(connection):
    return connection["platforminfo"]["name"], not(bool(connection["platforminfo"]["normal"]))


def is_match(stop, arrival_station):
    return stop.lower().startswith(arrival_station.lower())


def get_vehicle_stops(vehicle_id):
    """
    Get all the station a vehicle serves
    """
    try:
        v = requests.get(
                "http://api.irail.be/vehicle/",
                params={
                    "fast": "true",
                    "format": "json",
                    "id": vehicle_id}).json()
        return v["stops"]["stop"]
    except (KeyError, ValueError):
        return []  # error?


def vehicle_filter_check(vehicle_id, departure_station_name, arrival_station_name):
    """
    Checks whether a train passes
    a train station whose name starts with
    'arrival_station_name' after
    passing 'departure_station_name'
    """
    if not arrival_station_name:
        return True, None

    stops = get_vehicle_stops(vehicle_id)
    departure_station_passed = False

    for stop in stops:
        stop_name = stop["station"]
        stop_time = stop["time"]

        if stop_name == departure_station_name:
            departure_station_passed = True
        if departure_station_passed and is_match(stop["station"], arrival_station_name):
            arrival_time = parse_time(stop_time)
            return True, arrival_time
    return False, None


def make_station_header(json_object, destination_filter, vehicle_filter, context):
    """
    Make a header much like an actual
    liveboard in a train station.
    """
    name = json_object["stationinfo"]["standardname"]
    station_time = parse_time(json_object["timestamp"])
    direction = destination_filter or vehicle_filter or "all"
    title = name + " (direction: " + direction + ")"
    click.secho(station_time + " " +
                title.center(context.terminal_width - 6),
                reverse=True)
    return name


@click.command('liveboard')
@click.argument('station')
@click.option('--destination', '-d', default=None, multiple=True,
              help='Non-comprehensive but efficient filter that only checks the destination of each vehicle')
@click.option('--vehicle_filter', '-v', default=None,
              help='Comprehensive but inefficient filter that checks all stations of each vehicle')
@click.option('--continuous', '-c', is_flag=True,
              help='Refresh liveboard every 60 seconds',)
@pass_context
def cli(context, station, destination, vehicle_filter, continuous):
    """
    Show the upcoming trains for a certain trainstation.
    Very similar to what you would see on the screen
    in the station.
    Example:
    irail liveboard Gent-Sint-Pieters

    You can choose to refresh the livebaord
    every 60 seconds with the -c flag.
    Example:
    irail liveboard Gent-Sint-Pieters -c

    Additionally, you can filter the results
    based on destination.
    Example:
    irail liveboard Gent-Sint-Pieters --destination-filter Oostende
    or shorthand:
    irail liveboard Gent-Sint-Pieters -d Oostende

    You can select multiple destination-filters. If the train
    goes to any of the destinations, it will be shown on the liveboard.
    Example (all trains going to the beach):
    irail liveboard Gent-Sint-Pieters -d Oostende -d Blankenberge -d Knokke -d "De Panne"
    (note the "" for arguments with spaces in them)

    You can also use a more comprehensive check
    that checks every station on a vehicle's path,
    but this is very slow and generally not recommended.
    In most cases you're better off using the route command.
    Example:
    irail liveboard Gent-Sint-Pieters --vehicle-filter Aalter
    """
    # if station not found, give suggestions
    station = get_station(station)
    click.clear()
    while True:
        r = requests.get("http://api.irail.be/liveboard/",
                         params={"fast": "true",
                                 "format": "json",
                                 "station": station}).json()
        station_name = make_station_header(r, ','.join(destination), vehicle_filter, context)

        trains = safe_trains_extract(r)

        count = 0

        for train in trains:
            type_of_train = get_vehicle(train)
            normal_departure_time = get_time(train)
            cancelled, delay = get_delay(train)
            platform, platform_changed = get_platform(train)
            direction = get_direction(train)

            if destination and not any(direction.lower().startswith(d.lower()) for d in destination):
                continue

            vehicle_filter_passed, arrival_time = vehicle_filter_check(train["vehicle"], station_name, vehicle_filter)

            if not vehicle_filter_passed:
                continue

            message = (normal_departure_time +
                       (" - " + arrival_time if arrival_time else "") +
                       " " + delay + " " + type_of_train + " " + direction +
                       " " * (context.terminal_width - len(platform) - len(direction) - 13) +
                       click.style(platform, reverse=(True if platform_changed else False)))

            if cancelled:
                message = click.style(u'\u0336'.join(message) + '-' + u'\u0336', fg="red", blink=True)

            click.echo(message)
            count += 1
            if count >= context.terminal_height - 2:
                break

        if not continuous:
            break

        sleep(60)
        CURSOR_UP_ONE = '\x1b[1A'
        ERASE_LINE = '\x1b[2K'
        click.echo((CURSOR_UP_ONE + ERASE_LINE) * (len(trains) + 2))
