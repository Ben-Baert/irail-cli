import click
import requests
from .utils import *
from .cli import cli


def is_match(stop, arrival_station):
    return stop.lower().startswith(arrival_station.lower())


def get_vehicle_stops(vehicle_id):
    v = requests.get(
            "http://api.irail.be/vehicle/",
            params={
                "fast": "true",
                "format": "json",
                "id": vehicle_id}).json()
    return v["stops"]["stop"]


def vehicle_filter_check(vehicle_id, departure_station_name, arrival_station_name):
    """
    Checks whether a train passes
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
        if departure_station_passed and is_match(stop["station"], arrival_station):
            arrival_time = parse_timestamp(stop["time"])
            return True, arrival_time
    return False, None
    

def make_station_header(json_object, destination_filter, vehicle_filter):
    name = json_object["stationinfo"]["standardname"]
    station_time = parse_timestamp(json_object["timestamp"])
    msg = (name +
            (" (direction: " + (destination_filter or vehicle_filter) +")")
            if destination_filter or vehicle_filter else "")
    click.secho(station_time +
                " " +
                str.center(msg, TERMINAL_WIDTH - 6),
                reverse=True)
    return name


@cli.command()
@click.argument('station_suggestion')
@click.option('--destination_filter', '-f', default=None,
              help='Non-comprehensive but efficient filter that only checks the destination of each vehicle')
@click.option('--vehicle_filter', '-v', default=None,
              help='Comprehensive but inefficient filter that checks all stations of each vehicle')
@click.option('--continuous', '-c', flag=True,
              help='Refresh liveboard every 60 seconds',)
def liveboard(station_suggestion, destination_filter, vehicle_filter, continuous):
    # if station not found, give suggestions
    station = get_station(station_suggestion)
    click.clear()
    while True:
        r = requests.get("http://api.irail.be/liveboard/",
                         params={"fast": "true",
                                 "format": "json",
                                 "station": station}).json()
        station_name = make_station_header(r, destination_filter, vehicle_filter)

        trains = fetch_trains(r)

        for train in trains:
            type_of_train = parse_vehicle(train["vehicle"])
            normal_departure_time = parse_timestamp(train["time"])
            cancelled, delay = parse_delay(train["delay"])
            platform = parse_platform(train["platform"], train["platforminfo"]["normal"])            
            direction = parse_direction(train["station"])

            if destination_filter and not direction.startswith(destination_filter):
                continue

            vehicle_filter_passed, arrival_time = vehicle_filter_check(train["vehicle"], vehicle_filter, station_name)

            if not vehicle_filter_passed:
                continue

            message = (normal_departure_time +
                       (" - " + arrival_time if arrival_time else "") +
                       " " + delay + " " + type_of_train + " " + direction + platform)

            if cancelled:
                message = click.style('\u0336'.join(message) + '-' + '\u0336', fg="red", blink=True)
            
            click.echo(message)

        if not continuous:
            break

        sleep(60)
        CURSOR_UP_ONE = '\x1b[1A'
        ERASE_LINE = '\x1b[2K'
        click.echo((CURSOR_UP_ONE + ERASE_LINE) * (len(trains) + 2))