import requests
import click
import json

def get_json(feature, iid, extra_params=None):
    url = "http://api.irail.be/" + feature + "/"
    params = {"fast" : "true", "format" : "json", "lang" : "nl", "id" : iid}
    if extra_params:
        params.update(extra_params)
    r = requests.get(url, params)
    try:
        return r.json()
    except json.decoder.JSONDecodeError:
        click.echo("Something went wrong! There was no JSON returned by the iRail API!")
        click.echo("The system looked for " + feature + " " + iid)
        raise SystemExit(0)

def station_vehicles(station_id):
    """
    Get all vehicles that stop in a certain station
    """
    vehicles = []
    json_data = get_json("liveboard", station_id)
    try:
        for vehicle in json_data["departures"]["departure"]:
            vehicles.append({"vehicle": vehicle["vehicle"],
                             "destination" : vehicle["station"]})
    except KeyError:
        click.echo("No vehicles were found. This is likely because you ran this script at night, and there are no trains leaving soon. You should run this during the day in order to get relevant results.")
        raise SystemExit(0)

    return vehicles
    
def vehicle_stops(vehicle_id, station_name, max_time_secs=1800, include_locations=False):
    """
    Get all stops for one vehicle within a certain time range from one station 
    """
    def next_stops_only(stops):
        while True:
            stop = stops.pop(0)
            if stop["station"] == station_name:
                break
        return int(stops[0]["time"]), stops

    stops = {}
    if include_locations:
        vehicle = get_json("vehicle", vehicle_id, {"fast" : "false"})
    else:
        vehicle = get_json("vehicle", vehicle_id)

    #determine the time the vehicle stops in the station
    station_time_secs, next_vehicle_stops = next_stops_only(vehicle["stops"]["stop"])

    #determine stops within the time determined above
    for stop in next_vehicle_stops:
        raw_time = int(stop["time"])
        transit_time = raw_time - station_time_secs
        within_time_limit = transit_time <= max_time_secs
        if within_time_limit:
            if include_locations:
                stops["station_name"] = {"station_id" : stop["stationinfo"]["id"], 
                                         "lat" : stop["stationinfo"]["locationY"], 
                                         "lng" : stop["stationinfo"]["locationX"], 
                                         "time" : raw_time - station_time_secs}
            else:
                stops["station_name"] = transit_time
    
    return stops

def station_stops(station_id, station_name, max_time_secs=1800, include_locations=False):
    """
    Get all stops that are within a certain timerange from a station
    """
    vehicles = station_vehicles(station_id)
    destinations = {}

    for item in vehicles:
        stops = vehicle_stops(item["vehicle"], station_name, max_time_secs, include_locations)
        for stop in stops:
            current_station = stop["station_name"]
            if current_station not in destinations:
                destinations[current_station] = stop
            else:
                destinations[current_station]["time"] = 

    destinations = sorted(destinations, key=lambda k: k['time']) 

    return destinations

def get_station(suggestion):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    json_data = requests.get("https://irail.be/stations/NMBS/", {"q" : suggestion}, headers=headers).json()
    suggestions = json_data["@graph"]

    if len(suggestions) == 1:
        station_index = 0
            
    if len(suggestions) == 0:
        click.echo("No station like {0} found, please verify that you have an existing train station in Belgium and try again please.".format(suggestion))
        raise SystemExit(0)

    for index, station in enumerate(suggestions):
        click.echo(str(index) + ": " + station["name"])
    station_index = click.prompt('Which station do you mean by {0}?'.format(suggestion), type=int)

    return "BE.NMBS." + suggestions[station_index]["@id"][30:], suggestions[station_index]["name"]

@click.command()
@click.argument("station_suggestion", required=True, type=str)
@click.argument("timeframe_in_minutes", required=False, default=30, type=int)
@click.option('--include_locations', '-l', default=False, is_flag=True, help="Enable if you also want location information (lat/lng)")
def main(station_suggestion, timeframe_in_minutes, include_locations):
    station_id, station_name = get_station(station_suggestion)
    stops = station_stops(station_id, station_name, timeframe_in_minutes * 60, include_locations)
    for stop in stops:
        click.echo(stop["station_name"] + stop["time"])

if __name__ == '__main__':
    main()
    
