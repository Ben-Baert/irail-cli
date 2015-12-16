import requests
import click
import json
from collections import defaultdict
from time import sleep
from datetime import datetime, time
from geopy.distance import great_circle

def get_json(feature, id):
    if feature not in ["liveboard", "vehicle"]:
        raise ValueError("The feature should be 'liveboard' or 'vehicle'")

    url = "http://api.irail.be/" + feature + "/"
    params = {"fast" : "true", "format" : "json", "lang" : "nl", "id" : id}
    r = requests.get(url, params)
    try:
        return r.json()
    except json.decoder.JSONDecodeError:
        click.echo("Something went wrong! There was no JSON returned by the iRail API!")
        click.echo("The system looked for " + feature + " " + iid)
        raise SystemExit(0)

def station_vehicles(station_id, vehicles = []): #good reason for this!
    """
    Get all vehicles that stop in a certain station
    """
    json_data = get_json("liveboard", station_id)
    try:
        for vehicle in json_data["departures"]["departure"]:
            if vehicle["vehicle"] not in vehicles:
                vehicles.append(vehicle["vehicle"])
                                 
    except KeyError:
        click.echo("No vehicles were found. This is likely because you ran this script at night, and there are no trains leaving soon. You should run this during the day in order to get relevant results.")
        raise SystemExit(0)
    return vehicles
    
def vehicle_stops(vehicle_id, station_name, max_transit_time=1800):
    """
    Get all stops for one vehicle within a certain time range from one station 
    """    

    stops = {}
    vehicle = get_json("vehicle", vehicle_id)

    #determine the time the vehicle stops in the station
    all_vehicle_stops = vehicle["stops"]["stop"]
    while True:
        stop = all_vehicle_stops.pop(0)
        if stop["station"] == station_name:
            break
    station_time_secs =  int(stop["time"])
    next_vehicle_stops = all_vehicle_stops

    #determine stops within the time determined above
    for stop in next_vehicle_stops:
        raw_time = int(stop["time"])
        transit_time = raw_time - station_time_secs
        within_time_limit = transit_time <= max_transit_time
        if within_time_limit:
            current_station_name = stop["station"]
            stops[current_station_name] = {"transit_time" : transit_time,
                                           "departure_time" : datetime.fromtimestamp(raw_time).time()}
    
    return stops

def station_stops(station_id, station_name, max_transit_time=1800, vehicles=None):
    """
    Get all stops that are within a certain timerange from a station
    """

    def avg(*lst):
        return sum(lst) // len(lst)

    destinations = {}

    if not vehicles:
        vehicles = station_vehicles(station_id)
    
    click.echo("Checking vehicles:")
    with click.progressbar(vehicles) as vs:
        for vehicle in vs:
            stops = vehicle_stops(vehicle, station_name, max_transit_time)
            for station, data in stops.items():
                if station not in destinations:
                    destinations[station] = {"transit_time"     : data["transit_time"],
                                             "departure_times"  : [data["departure_time"]]}
                else:
                    destinations[station]["transit_time"] = avg(destinations[station]["transit_time"], data["transit_time"])
                    destinations[station]["departure_times"] += [data["departure_time"]]
    
    return destinations

def process_destinations(destinations, include_locations=False, station_location=None):
    processed = []
    click.echo("Processing destinations:")
    with click.progressbar(destinations.items()) as ds:
        for destination, data in ds:
            transit_time = data["transit_time"] // 60
            departure_times = data["departure_times"]
            overall_frequency = len(departure_times)
            morning_frequency = 0
            evening_frequency = 0
            for dep_time in departure_times:
                if time(7,0) <= dep_time <= time(9,0):
                    morning_frequency += 1
                if time(17,0) <= dep_time <= time(19,0):
                    evening_frequency += 1
            score = transit_time // overall_frequency
            if include_locations:
                destination_location = get_lat_lng(destination["station_id"])
                distance = get_distance(station_location, destination)
            processed.append((destination, score, transit_time, overall_frequency, morning_frequency, evening_frequency))

    return sorted(processed, key=lambda x: x[1])


def show_station_stops(stations):
    click.secho("Station".ljust(20) + "Avg. transit time".ljust(20) + "Overall frequency", reverse = True)
    for station, score, avg_transit_time, overall_frequency, morning_frequency, evening_frequency in stations:
        click.echo(station.ljust(25) + str(avg_transit_time).ljust(20) + str(overall_frequency))

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

    return "BE.NMBS." + suggestions[station_index]["@id"][30:], suggestions[station_index]["name"]

def get_lat_lng(station_name):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    params = {"q" : station_name}
    json_data = requests.get("https://irail.be/stations/NMBS/", params, headers=headers).json()
    print(json_data)
    lat = json_data["@graph"][0]["lattitude"]
    lng = json_data["@graph"][0]["longitude"]
    return lat, lng

def get_distance(station_one_id, station_two_id):
    station_one_location = get_lat_lng(station_one_id)
    station_two_location = get_lat_lng(station_two_id)
    return great_circle(station_one_location, station_two_location).meters


@click.command()
@click.argument("station_suggestion", required=True, type=str)
@click.argument("max_transit_time_in_minutes", required=False, default=30, type=int)
@click.option("--day", "-d", is_flag=True, default=False, required=False)
@click.option("--include_locations", "-l", is_flag=True, default=False, required=False)
def main(station_suggestion, max_transit_time_in_minutes, day, include_locations):
    station_id, station_name = get_station(station_suggestion)
    vehicles = None
    station_location = None
    if day:
        click.echo("Checking for a whole day...")
        with click.progressbar(range(24)) as hours:
            for _ in hours:
                vehicles = station_vehicles(station_id)
                sleep(3600)
    stops = station_stops(station_id, station_name, max_transit_time_in_minutes * 60, vehicles)
    if include_locations:
        station_location = get_lat_lng(station_id)
    processed_stops = process_destinations(stops, include_locations, station_location)

    show_station_stops(processed_stops)

if __name__ == '__main__':
    main()
