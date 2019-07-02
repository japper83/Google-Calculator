import googlemaps
import datetime
import oyaml as yaml
import os


def google_maps_calculator():
    def read_data(filename):
        data_file = filename
        with open(data_file, 'r') as f:
            data = yaml.safe_load(f)
        return data

    def table_info(filename):
        if not os.path.isfile("traffic_data/" + filename):
            table_head = "Date, Time, Distance in meters, Duration in seconds"
            f = open("traffic_data/" + filename, 'a')
            f.write(table_head + "\n")
            f.close()

    settings = read_data("settings.yaml")
    now = datetime.datetime.now()
    # Declarations
    token = settings["apitoken"][0]  # Enter your Google API Token'
    # get Client object
    client = googlemaps.Client(key=token)
    # Get directions
    time = now.strftime("%H:%M:%S")
    date = now.strftime("%d:%m:%Y")

    data = read_data("data.yaml")
    for routes in data["routes"]:
        table_info(routes["filename"] + ".csv")
        directions = client.distance_matrix(routes["start"], routes["end"], departure_time=now)
        result = date + "," + time + "," + str(directions["rows"][0]["elements"][0]["distance"]["value"]) + "," + str(
            directions["rows"][0]["elements"][0]["duration_in_traffic"]["value"])

        f = open("traffic_data/" + routes["filename"] + ".csv", 'a')
        f.write(result + "\n")
        f.close()
