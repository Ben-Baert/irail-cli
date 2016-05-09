import click
import re
from irail.cli import pass_context
from irail.commands.utils import *


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


def generate_vehicle_string(connection, include_number):
    vehicle = get_vehicle(connection, include_number=include_number)
    direction = get_direction(connection)

    return u'\u2193 ' + vehicle + " (" + direction + ") " + u'\u2193'

def generate_departure_vehicle_string(connection, include_number):
    pass


def get_stops_for_via(via):
    pass


def get_stops_for_vehicle(vehicle):
    pass


def show_stop(vehicle_stop):
    pass


def show_stops(context, via, from_station=None, to_station=None):
    vehicle = via["vehicle"]
    from_station = ""


def expand_via(context, via, show_vehicle):
    station_name = get_station_name(via)

    arrival_time = get_arrival_time(via)
    arrival_platform = get_arrival_platform(via)

    departure_time = get_departure_time(via)
    departure_platform = get_departure_platform(via)

    vehicle_string = generate_vehicle_string(via, include_number=show_vehicle)
    centered_vehicle_string = vehicle_string.center(context.terminal_width)

    if via["id"] != "0":
        click.secho(centered_vehicle_string, reverse=True)

    arrival_string = arrival_time + " " + arrival_platform
    departure_string = departure_time + " "  + departure_platform

    click.echo(station_name +  (arrival_string + " | " + departure_string).rjust(context.terminal_width - len(station_name)))


def get_info(info):
    station = info["stationinfo"]["standardname"]
    time = timestamp_to_human_readable_time(info["time"])
    platform = get_platform(info)
    direction = info["direction"]["name"]
    return station, time, platform, direction


def get_departure_info(connection):
    return get_info(connection["departure"])


def get_arrival_info(connection):
    return get_info(connection["arrival"])


def expand_connection(context, connection, show_vehicle):
    d_station, d_time, d_platform, d_direction = get_departure_info(connection)

    a_station, a_time, a_platform, a_direction = get_arrival_info(connection)

    click.echo(d_station + (d_time + " " + d_platform).rjust(context.terminal_width - len(d_station)))

    departure_vehicle_string = generate_vehicle_string(departure_info, include_number=show_vehicle)
    click.secho(departure_vehicle_string.center(context.terminal_width), reverse=True)
    if "vias" in connection:
        for via in connection["vias"]["via"]:
            expand_via(context, via, show_vehicle)
        arrival_vehicle_string = generate_vehicle_string(arrival_info, include_number=show_vehicle)
        click.secho(arrival_vehicle_string.center(context.terminal_width), reverse=True)

    (click.echo(a_station + (a_time + " " + a_platform + (" " * 12))
              .rjust(context.terminal_width - len(arrival_station))))


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
        d_station, d_time, d_platform, d_direction = get_departure_info(connection)
        a_station, a_time, a_platform, a_direction = get_arrival_info(connection)
        duration = get_duration(connection)
        nr_of_vias = get_nr_of_vias(connection)

        msg = str(index) + ": " + departure_time + " --> " + arrival_time + "             " + str(duration) + "     " +  str(nr_of_vias)
        click.echo(msg)


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
@click.option('--show-vehicle', '-v', default=False, is_flag=True)
@pass_context
def cli(context, from_station, to_station, time, date, selection, show_vehicle):
    if not verify_date(date):
        click.echo("Date is not properly formatted (DDMMYY)")
        raise SystemExit(1)
    if not verify_time(time):
        click.echo("Time is not properly formatted (HHMM)")
        raise SystemExit(1)
    from_station = get_station(from_station)
    to_station = get_station(to_station)

    make_route_header(context, from_station, to_station)

    connections = route_request(from_station, to_station, date, time, selection)

    optimal_connections = sort_connections(connections)
    most_optimal_connection = optimal_connections.pop(0)
    optimal_departure_time, optimal_arrival_time, duration, changes = route_overview(most_optimal_connection)
    click.secho("Optimal connection: " + optimal_departure_time + " --> " + optimal_arrival_time + ("Duration: " + duration + " " + "Changes: " + changes).rjust(context.terminal_width - 35), reverse = True, nl = False)
    expand_connection(context, most_optimal_connection, show_vehicle=show_vehicle)

    click.echo("Other options:")
    show_route_choices(optimal_connections)

    v = click.confirm('Would you like to expand any of these?', abort=True)
    while v:
        e = click.prompt("Which one (type 9 for all)?", type=int)
        if e == 9:
            for connection in optimal_connections:
                expand_connection(context, connection, show_vehicle=show_vehicle)
            raise SystemExit(1)
        current = optimal_connections.pop(e)
        expand_connection(context, current, show_vehicle=show_vehicle)
        show_route_choices(optimal_connections)
        if optimal_connections:
            v = click.confirm('Would you like to expand any more?', abort=True)
        else:
            click.echo("These were all the connections!")
