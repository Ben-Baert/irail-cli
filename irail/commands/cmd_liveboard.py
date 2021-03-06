import click
import requests
from time import sleep
from irail.cli import pass_context
from irail.commands.utils import *


def get_direction_from_connection(connection):
    return connection["stationinfo"]["name"]


def get_platform_from_connection(connection):
    return connection["platforminfo"]["name"], not(bool(connection["platforminfo"]["normal"]))


def make_station_header(json_object, destination_filter, context):
    """
    Make a header much like an actual
    liveboard in a train station.
    """
    name = json_object["stationinfo"]["standardname"]
    station_time = timestamp_to_human_readable_time(json_object["timestamp"])
    direction = destination_filter or "all"
    title = name + " (direction: " + direction + ")"
    click.secho(station_time + " " +
                title.center(context.terminal_width - 6),
                reverse=True)
    return name


@click.command('liveboard')
@click.argument('station')
@click.option('--destination', '-d', default=None, multiple=True,
              help='Non-comprehensive but efficient filter that only checks the destination of each vehicle')
@click.option('--train-type', '-t', default=None, multiple=True,
              help='Filter on train type (e.g. IC, L, S)')
@click.option('--show-vehicle', '-v', is_flag=True,
              help="Show vehicle ids")
@click.option('--continuous', '-c', is_flag=True,
              help='Refresh liveboard every 60 seconds',)
@pass_context
def cli(context, station, destination, train_type, show_vehicle, continuous):
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
    """
    # if station not found, give suggestions
    station = get_station_from_user_input(station)
    click.clear()
    while True:
        r = requests.get("http://api.irail.be/liveboard/",
                         params={"fast": "true",
                                 "format": "json",
                                 "station": station}).json()
        station_name = make_station_header(r, ','.join(destination), context)

        trains = safe_trains_extract(r)

        count = 0
        for train in trains:
            type_of_train = get_human_readable_vehicle_from_connection(train, include_number=show_vehicle)
            if train_type and not any(type_of_train.startswith(tt) for tt in train_type):
                continue
            normal_departure_time = get_time_from_connection(train)
            cancelled, delay = get_human_readable_delay_from_connection(train)
            platform, platform_changed = get_platform_from_connection(train)
            direction = get_direction_from_connection(train)

            if destination and not any(direction.lower().startswith(d.lower()) for d in destination):
                continue

            message = (normal_departure_time +
                       " " + delay + " " + type_of_train.rjust(7) + " " + direction +
                       " " * (context.terminal_width - len(platform) - len(direction) - 18))

            if cancelled:
                message += platform
                message = click.style(u'\u0336'.join(message), fg="red", blink=True)
            else:
                message += click.style(platform, reverse=(True if platform_changed else False))

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
