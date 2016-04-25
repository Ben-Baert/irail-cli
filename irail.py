import click
import requests
from datetime import datetime, timedelta
from time import sleep


TERMINAL_WIDTH, TERMINAL_HEIGHT = click.get_terminal_size()


def parse_timestamp(seconds_str):
    return datetime.fromtimestamp(int(seconds_str)).strftime("%H:%M")


def make_station_header(json_object, direction_filter, vehicle_filter):
    name = json_object["stationinfo"]["standardname"]
    station_time = parse_timestamp(json_object["timestamp"])
    msg = name + (" (direction: " + (direction_filter or vehicle_filter) + ")") if direction_filter or vehicle_filter else ""
    click.secho(station_time + " " + str.center(msg, TERMINAL_WIDTH - 6), reverse = True)
    return name


def fetch_trains(json_object):
    try:
        trains = json_object["departures"]["departure"]
        return trains
    except KeyError:
        click.echo("No trains!")
        return []


def parse_vehicle(vehicle_id_string):
    return ''.join(x for x in vehicle_id_string[8:10] if x in "PLIC").ljust(2)


def get_station(suggestion):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    json_data = requests.get("https://irail.be/stations/NMBS/", {"q" : suggestion}, headers=headers).json()
    suggestions = json_data["@graph"]

    if len(suggestions) == 1:
        station_index = 0
            
    elif len(suggestions) == 0:
        click.echo("No station like {0} found, please verify that you have an existing train station in Belgium and try again please.".format(suggestion))
        raise SystemExit(0)
    else:
        for index, station in enumerate(suggestions):
            click.echo(str(index) + ": " + station["name"])
        station_index = click.prompt('Which station do you mean by {0}?'.format(suggestion), type=int)

    return suggestions[station_index]["name"]


def parse_delay(delay_str):
    cancelled = False
    if delay_str == "0":
        return False, "   "
    elif delay_str == "cancel":
        return True, 0
    else:
        delay = int(delay_str) // 60
        text = ("+" + str(delay)).ljust(3)
        return False, click.style(text, fg = "red")


def parse_platform(train):
    platform = train["platform"]
    platform_changed = train["platforminfo"]["normal"] != "1"
    platform_message = " " + platform.rjust(2)
    if platform_changed:
        return click.style(platform_message, reverse = True)
    return platform_message


def vehicle_filter_check(train, vehicle_filter):
    if vehicle_filter:
        vehicle_id = train["vehicle"]
        v = requests.get("http://api.irail.be/vehicle/", params = {"fast" : "true", "format" : "json", "id" : vehicle_id}).json()
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


@click.command()
@click.argument('station_suggestion')
@click.option('--direction_filter', '-f', default=None)
@click.option('--vehicle_filter', '-v', default=None)
@click.option('--continuous', '-c')#, flag=True, default=False)
def liveboard(station_suggestion, direction_filter, vehicle_filter, continuous):
    # if station not found, give suggestions
    station = get_station(station_suggestion)
    click.clear()
    while True:

        r = requests.get("http://api.irail.be/liveboard/", 
                               params = {"fast" : "true", "format" : "json", "station" : station}).json()
        station_name = make_station_header(r, direction_filter, vehicle_filter)

        trains = fetch_trains(r)

        for train in trains:
            type_of_train = parse_vehicle(train["vehicle"])

            normal_departure_time = datetime.fromtimestamp(int(train["time"])).strftime("%H:%M")

            cancelled, delay = parse_delay(train["delay"])

            platform = parse_platform(train)
            
            direction = train["station"].ljust(40)

            if direction_filter and not direction.startswith(direction_filter):
                continue

            vehicle_filter_passed, arrival_time = vehicle_filter_check(train, vehicle_filter)

            if not vehicle_filter_passed:
                continue

            message = normal_departure_time + (" - " + arrival_time if arrival_time else "") + " " + delay + " " + type_of_train + " " + direction + platform

            if cancelled:
                message = click.style('\u0336'.join(message) + '-' + '\u0336', fg = "red", blink = True)
            
            click.echo(message)
        
        if not continuous:
            break

        sleep(60)
        CURSOR_UP_ONE = '\x1b[1A'
        ERASE_LINE = '\x1b[2K'
        click.echo((CURSOR_UP_ONE + ERASE_LINE) * (len(trains) + 2))

            
def parse_vias(connection):
    if "vias" in connection:
        return int(connection["vias"]["number"])
    return 0 


def expand_via(via):
    station_name = via["stationinfo"]["standardname"]

    arrival_time = parse_timestamp(via["arrival"]["time"])
    arrival_platform = parse_platform(via["arrival"])

    departure_time = parse_timestamp(via["departure"]["time"])
    departure_platform = parse_platform(via["departure"])

    vehicle = parse_vehicle(via["vehicle"])
    direction = via["direction"]["name"]

    click.secho(str.center('\u2193 ' + vehicle + " (" + direction + ") \u2193", TERMINAL_WIDTH), reverse = True) if via["id"] != "0" else False
    click.echo(station_name +  (arrival_time + " " + arrival_platform + " | " + departure_time + " "  + departure_platform).rjust(TERMINAL_WIDTH - len(station_name)))
    

def parse_duration(duration: str) -> str:
    hours, minutes = divmod(int(duration), 3600)
    return str(hours) + ":" + str(minutes)[:-2].rjust(2, "0")


def expand_connection(connection: dict) -> None:
    departure_info = connection["departure"]
    departure_station = departure_info["stationinfo"]["standardname"]
    departure_time = parse_timestamp(departure_info["time"])
    departure_vehicle = parse_vehicle(departure_info["vehicle"])
    departure_platform = parse_platform(departure_info)
    departure_direction = departure_info["direction"]["name"]
    
    arrival_info = connection["arrival"]
    arrival_station = arrival_info["stationinfo"]["standardname"]
    arrival_time = parse_timestamp(arrival_info["time"])
    arrival_vehicle = parse_vehicle(arrival_info["vehicle"])
    arrival_platform = parse_platform(arrival_info)
    arrival_direction = arrival_info["direction"]["name"]

    empty_slot = " " * 10
    duration = parse_duration(connection["duration"])
    nr_of_vias = parse_vias(connection)

    click.echo(departure_station + (departure_time + " "  + departure_platform).rjust(TERMINAL_WIDTH - len(departure_station)))
    click.secho(str.center('\u2193 ' + departure_vehicle + " (" + departure_direction + ") \u2193", TERMINAL_WIDTH), reverse = True)
    if "vias" in connection:
        for via in connection["vias"]["via"]:
            expand_via(via)
    click.secho(str.center('\u2193 ' + arrival_vehicle + " (" + arrival_direction + ") \u2193", TERMINAL_WIDTH), reverse = True)
    click.echo(arrival_station + (arrival_time + " " + arrival_platform+ empty_slot).rjust(TERMINAL_WIDTH - len(arrival_station)))


def make_route_header(from_station, to_station):
    click.secho(" " * TERMINAL_WIDTH, reverse = True)
    click.secho(str.center(from_station + " - " + to_station, TERMINAL_WIDTH), reverse =True)
    click.secho(" " * TERMINAL_WIDTH, reverse = True)


def route_overview(connection: dict) -> tuple:
    return (parse_timestamp(connection["departure"]["time"]), 
            parse_timestamp(connection["arrival"]["time"]),
            str(parse_duration(connection["duration"])),
            str(parse_vias(connection)))


def show_route_choices(connections: list) -> None:
    for index, connection in enumerate(connections):
        departure_info = connection["departure"]
        departure_time = parse_timestamp(departure_info["time"])
        departure_platform = departure_info["platform"]
        departure_direction = departure_info["direction"]
        arrival_info = connection["arrival"]
        arrival_time = parse_timestamp(arrival_info["time"])
        arrival_platform = arrival_info["platform"]
        duration = int(connection["duration"]) // 60
        nr_of_vias = parse_vias(connection)

        msg = str(index) + ": " + departure_time + " --> " + arrival_time + "             " + str(duration) + "     " +  str(nr_of_vias)
        click.echo(msg)


@click.command()
@click.argument('from_station_suggestion')
@click.argument('to_station_suggestion')
@click.option('--time', '-t', default = None)
@click.option('--date', '-d', default = None)
@click.option('--selection', '-s', default = 'depart', type = click.Choice(['depart', 'arrive']))
def route(from_station_suggestion, to_station_suggestion, time, date, selection):
    from_station = get_station(from_station_suggestion)
    to_station = get_station(to_station_suggestion)
    make_route_header(from_station, to_station)
    params = {"from" : from_station, 
              "to" : to_station, 
              "time" : time, 
              "date" : date, 
              "timeSel" : selection, 
              "format" : "json", 
              "fast" : "true"}
    r = requests.get("http://api.irail.be/connections/", params = params).json()
    
    if not "connection" in r:
        click.echo("No routes found!")
        return False

    connections = r["connection"]

    optimal_connections = sorted(connections, key = lambda x: int(x["arrival"]["time"]) + int(x["duration"]) // 2)
    most_optimal_connection = optimal_connections.pop(0)
    optimal_departure_time, optimal_arrival_time, duration, changes = route_overview(most_optimal_connection)
    click.secho("Optimal connection: " + optimal_departure_time + "-->" + optimal_arrival_time + (duration + " " + changes).rjust(TERMINAL_WIDTH - 33), reverse = True, nl = False)
    expand_connection(most_optimal_connection)

    click.echo("Other options:")
    show_route_choices(optimal_connections)
    
    v = click.confirm('Would you like to expand any of these?', abort = True)
    while v:
        e = click.prompt("Which one (type 9 for all)?", type = int)
        if e == 9:
            for connection in optimal_connections:
                expand_connection(connection)
            return True
        current = optimal_connections.pop(e)
        expand_connection(current)
        show_route_choices(optimal_connections)
        if optimal_connections:
            v = click.confirm('Would you like to expand any more?', abort = True)
        else:
            click.echo("These were all the connections!")


@click.command()
@click.argument('vehicle_id')
def vehicle(vehicle_id):
    r = requests.get("http://api.irail.be/vehicle/", params = {"id" : vehicle_id, "format" : "json", "fast" : "true"}).json()
    click.secho(parse_timestamp(r["timestamp"]) + " " + str.center(r["vehicle"], TERMINAL_WIDTH - 6), reverse = True)
    now = datetime.now()
    for stop in r["stops"]["stop"]:
        stop_time = parse_timestamp(stop["time"])
        if (datetime.fromtimestamp(int(stop["time"])) + timedelta(seconds = int(stop["delay"]))) < now:
            dim = True
        else:
            dim = False
        click.secho(stop_time + parse_delay(stop["delay"])[1] + stop["station"], dim = dim)

if __name__ == '__main__':
    route()

