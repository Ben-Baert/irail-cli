import click
import re
from irail.cli import pass_context
from irail.commands.utils import *


class NoConnectionsFound(Exception):
    pass


def parse_duration(duration):
    hours, minutes = divmod(int(duration), 3600)
    return str(hours) + ":" + str(minutes // 60).rjust(2, "0")


def get_duration(connection):
    return parse_duration(connection["duration"])


def get_nr_of_vias(connection):
    try:
        return int(connection["vias"]["number"])
    except KeyError:
        return 0


def get_direction(connection):
    return connection["direction"]["name"]

def generate_vehicle_string(connection):
    vehicle = get_vehicle(connection)
    direction = get_direction(connection)

    return u'\u2193 ' + vehicle + " (" + direction + ") " + u'\u2193'

def expand_via(context, via):
    station_name = get_station_name(via)

    arrival_time = get_arrival_time(via)
    arrival_platform = get_arrival_platform(via)

    departure_time = get_departure_time(via)
    departure_platform = get_departure_platform(via)

    vehicle = get_vehicle(via)
    direction = get_direction(via)

    vehicle_string = generate_vehicle_string(via)
    centered_vehicle_string = vehicle_string.center(context.terminal_width)

    station_string = ""

    if via["id"] != "0":
        click.secho(centered_vehicle_string, reverse=True)

    arrival_string = arrival_time + " " + arrival_platform
    departure_string = departure_time + " "  + departure_platform

    click.echo(station_name +  (arrival_string + " | " + departure_string).rjust(context.terminal_width - len(station_name)))


def expand_connection(context, connection):
    """
    Get rid of duplication
    """
    departure_info = connection["departure"]
    departure_station = departure_info["stationinfo"]["standardname"]
    departure_time = parse_time(departure_info["time"])
    departure_vehicle = parse_vehicle(departure_info["vehicle"])
    departure_platform = get_platform(departure_info)
    departure_direction = departure_info["direction"]["name"]

    arrival_info = connection["arrival"]
    arrival_station = arrival_info["stationinfo"]["standardname"]
    arrival_time = parse_time(arrival_info["time"])
    arrival_vehicle = parse_vehicle(arrival_info["vehicle"])
    arrival_platform = get_platform(arrival_info)
    arrival_direction = arrival_info["direction"]["name"]

    empty_slot = " " * 12
    duration = get_duration(connection)
    nr_of_vias = get_nr_of_vias(connection)

    click.echo(departure_station + (departure_time + " "  + departure_platform).rjust(context.terminal_width - len(departure_station)))
    departure_vehicle_string = generate_vehicle_string(departure_info)
    click.secho(departure_vehicle_string.center(context.terminal_width), reverse=True)
    if "vias" in connection:
        for via in connection["vias"]["via"]:
            expand_via(context, via)
        arrival_vehicle_string = generate_vehicle_string(arrival_info)
        click.secho(arrival_vehicle_string.center(context.terminal_width), reverse = True)
    click.echo(arrival_station + (arrival_time + " " + arrival_platform + empty_slot).rjust(context.terminal_width - len(arrival_station)))


def make_route_header(context, from_station, to_station):
    click.secho(" " * context.terminal_width, reverse=True)
    route_string = from_station + " - " + to_station
    click.secho(route_string.center(context.terminal_width), reverse=True)
    click.secho(" " * context.terminal_width, reverse=True)


def route_overview(connection):
    return (get_departure_time(connection),
            get_arrival_time(connection),
            get_duration(connection),
            str(get_nr_of_vias(connection)))


def show_route_choices(connections):
    for index, connection in enumerate(connections):
        departure_info = connection["departure"]
        departure_time = parse_time(departure_info["time"])
        departure_platform = departure_info["platform"]
        departure_direction = departure_info["direction"]
        arrival_info = connection["arrival"]
        arrival_time = parse_time(arrival_info["time"])
        arrival_platform = arrival_info["platform"]
        duration = get_duration(connection)
        nr_of_vias = get_nr_of_vias(connection)

        msg = str(index) + ": " + departure_time + " --> " + arrival_time + "             " + str(duration) + "     " +  str(nr_of_vias)
        click.echo(msg)


def get_connections(from_station, to_station, time=None, date=None, time_preference="depart"):  # , format="json", fast=True
    params = {"from": from_station,
              "to": to_station,
              "time": time,
              "date": date,
              "timeSel": time_preference,
              "format": "json",
              "fast": "true"}
    r = requests.get("http://api.irail.be/connections/", params=params).json()
    try:
        return r["connection"]
    except KeyError:
        raise NoConnectionsFound


def verify_date(date):
    if not date:
        return True

    r = re.match(r'^(\d{2})(\d{2})(\d{2})$', date)
    if not r:
        return False

    day_is_acceptable = int(r.group(1)) in range(1, 32)
    month_is_acceptable = int(r.group(2)) in range(1, 13)
    year_is_acceptable = int(r.group(3)) in (datetime.now().year % 100 - i for i in (-1, 0, 1))

    return day_is_acceptable and month_is_acceptable and year_is_acceptable


def verify_time(time):
    if not time:
        return True

    r = re.match(r'^(\d{2})(\d{2})$', time)
    if not r:
        return False

    hour_is_acceptable = int(r.group(1)) in range(0, 24)
    minutes_is_acceptable = int(r.group(2)) in range(0, 60)

    return hour_is_acceptable and minutes_is_acceptable


def asap_sort(connection):
    return connection["arrival"]["time"]


def reasonable_connection(connection):
    return int(connection["arrival"]["time"]) + int(connection["duration"]) // 2


def sort_connections(connections):
    return sorted(connections, key=reasonable_connection)



@click.command()
@click.argument('from_station')
@click.argument('to_station')
@click.option('--time', '-t', default=None,
              help="Format: HHMM. Defaults to current time")
@click.option('--date', '-d', default=None,
              help="Format: DDMMYY. Defaults to current date")
@click.option('--selection', '-s', default='depart', type=click.Choice(['depart', 'arrive']),
              help="Choose 'depart' or 'arrive' at specified date/time. Defaults to 'depart'")
@pass_context
def cli(context, from_station, to_station, time, date, selection):
    if not verify_date(date):
        click.echo("Date is not properly formatted (DDMMYY)")
        raise SystemExit(0)
    if not verify_time(time):
        click.echo("Time is not properly formatted (HHMM)")
        raise SystemExit(0)
    from_station = get_station(from_station)
    to_station = get_station(to_station)

    make_route_header(context, from_station, to_station)

    connections = get_connections(from_station, to_station, time, date, selection)

    optimal_connections = sort_connections(connections)
    most_optimal_connection = optimal_connections.pop(0)
    optimal_departure_time, optimal_arrival_time, duration, changes = route_overview(most_optimal_connection)
    click.secho("Optimal connection: " + optimal_departure_time + " --> " + optimal_arrival_time + ("Duration: " + duration + " " + "Changes: " + changes).rjust(context.terminal_width - 35), reverse = True, nl = False)
    expand_connection(context, most_optimal_connection)

    click.echo("Other options:")
    show_route_choices(optimal_connections)

    v = click.confirm('Would you like to expand any of these?', abort=True)
    while v:
        e = click.prompt("Which one (type 9 for all)?", type=int)
        if e == 9:
            for connection in optimal_connections:
                expand_connection(context, connection)
            raise SystemExit(0)
        current = optimal_connections.pop(e)
        expand_connection(context, current)
        show_route_choices(optimal_connections)
        if optimal_connections:
            v = click.confirm('Would you like to expand any more?', abort=True)
        else:
            click.echo("These were all the connections!")
