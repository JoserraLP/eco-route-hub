import time

from flask import Blueprint, jsonify, request

from route_consumption_estimator.api.models import Vehicle
from route_consumption_estimator.api.security import api_required
from route_consumption_estimator.api.utils import request_routes, process_route_information, \
    estimate_consumption_routes
from route_consumption_estimator.vehicle.veh_model import VehicleModel

# routes blueprint
routes_bp = Blueprint('routes', __name__)


@routes_bp.route('/routes', methods=['GET'])
@api_required
def calculate_route_estimation():
    start_time = time.time()
    # Coords are LAT,LON
    source = request.args.get('source')
    destination = request.args.get('destination')
    inner_coords = request.args.get('inner_coords', '')
    user_id = request.args.get('user_id', '')
    vehicle_id = request.args.get('vehicle_id', '')
    additional_mass = request.args.get('additional_mass', '')

    coordinates = f'{source};{inner_coords};{destination}' if inner_coords else f'{source};{destination}'

    routes = request_routes(coordinates)

    routes_information = process_route_information(routes)

    # Get vehicle to simulate
    vehicle = Vehicle.query.get(vehicle_id)

    # Update the vehicle A value with the additional mass
    if additional_mass:
        vehicle.recalculate_a(int(additional_mass))

    # Create a vehicle using the simulator model
    simulator_vehicle = VehicleModel(total_veh_mass=int(vehicle.UnladenVehMass+int(additional_mass)),
                                     avg_consumption=float(vehicle.AvgConsumption),
                                     p_max_kw=float(vehicle.PMaxKw),
                                     A=float(vehicle.A),
                                     B=float(vehicle.B),
                                     C=float(vehicle.C),
                                     motor_type=str(Vehicle.MotorType))

    estimations = estimate_consumption_routes(routes, routes_information, simulator_vehicle)

    # Merge both routes and estimations
    routes_estimations = [{**x, **y} for x, y in zip(routes, estimations)]

    # print(routes_estimations)

    # Filter the route: Eco, Shortest and Fastest
    consumption_index = min(enumerate(routes_estimations), key=lambda x: x[1]['energy_consumption'])[0]
    distance_index = min(enumerate(routes_estimations), key=lambda x: x[1]['distance'])[0]
    time_index = min(enumerate(routes_estimations), key=lambda x: x[1]['time'])[0]

    # Define final routes
    final_routes = {
        'eco': estimations[consumption_index],
        'shortest': estimations[distance_index],
        'fastest': estimations[time_index]
    }

    # f'ROUTES_INFO: {[(route["router_distance"], route["router_duration"]) for route in routes]}' \
    #            f'\n Estimations: {estimations} with elapsed time {time.time() - start_time}'

    return final_routes
