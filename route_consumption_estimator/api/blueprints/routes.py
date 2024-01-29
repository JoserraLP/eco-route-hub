import time

from flask import Blueprint, jsonify, request
from route_consumption_estimator.api.security import api_required
from route_consumption_estimator.api.utils import load_all_vehicles, request_routes, process_route_information, \
    load_vehicle, estimate_consumption_routes

# routes blueprint
routes_bp = Blueprint('routes', __name__)

VEHICLES_DIR = '../../experiments_november/vehicles.json'
all_vehicles_data = load_all_vehicles(VEHICLES_DIR)


@routes_bp.route('/routes', methods=['GET'])
@api_required
def calculate_route_estimation():
    start_time = time.time()
    # Coords are LAT,LON
    source = request.args.get('source')
    destination = request.args.get('destination')
    inner_coords = request.args.get('inner_coords', '')
    vehicle_id = request.args.get('VehicleID', '')

    coordinates = f'{source};{inner_coords};{destination}' if inner_coords else f'{source};{destination}'

    routes = request_routes(coordinates)

    routes_information = process_route_information(routes)

    vehicle = load_vehicle(all_vehicles_data, vehicle_id=vehicle_id)

    estimations = estimate_consumption_routes(routes, routes_information, vehicle)

    return f'ROUTES_INFO: {[(route["router_distance"], route["router_duration"]) for route in routes]}' \
           f'\n Estimations: {estimations} with elapsed time {time.time() - start_time}'
