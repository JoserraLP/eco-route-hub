from flask import Flask, request, jsonify

from route_consumption_estimator.api.utils import *

app = Flask(__name__)

VEHICLES_DIR = '../../experiments_november/vehicles.json'
all_vehicles_data = load_all_vehicles(VEHICLES_DIR)


@app.route('/routes', methods=['GET'])
def calculate_route_estimation():
    # Coords are LAT,LON
    source = request.args.get('source')
    destination = request.args.get('destination')
    inner_coords = request.args.get('inner_coords', '')
    vehicle_id = request.args.get('vehicle_id', '')

    coordinates = f'{source};{inner_coords};{destination}' if inner_coords else f'{source};{destination}'

    routes = request_routes(coordinates)

    routes_information = process_route_information(routes)

    vehicle = load_vehicle(all_vehicles_data, vehicle_id=vehicle_id)

    estimations = estimate_consumption_routes(routes_information, vehicle)

    return estimations


if __name__ == "__main__":
    app.run(debug=True)
    # flask run
