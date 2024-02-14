import json

import polyline

from route_consumption_estimator.engine.route_engine import EcoTrafficEngine
from route_consumption_estimator.estimator.estimator import get_routes_graphhopper, get_routes_osrm, get_routes_ors
from route_consumption_estimator.graph.models import Coords
from route_consumption_estimator.path.path_model import PathModel
from route_consumption_estimator.vehicle.constants import AREA_FACTOR
from route_consumption_estimator.vehicle.power_energy import PowerEnergyEstimator
from route_consumption_estimator.vehicle.speed_profile import SpeedProfile
from route_consumption_estimator.vehicle.veh_model import VehicleModel


def load_all_vehicles(vehicles_dir):
    with open(vehicles_dir) as f:
        all_vehicles_data = json.load(f)

    return all_vehicles_data


def request_routes(coordinates: str):
    route_coordinates = [Coords(lat=float(coordinates.split(',')[0]), lon=float(coordinates.split(',')[1]))
                         for coordinates in coordinates.split(';')]

    """
    routes = get_routes_graphhopper(route_coordinates) + get_routes_osrm(route_coordinates) + \
             get_routes_ors(route_coordinates)
    """

    routes = get_routes_osrm(route_coordinates)

    return routes


def process_route_information(routes: list):
    # Start Eco-Traffic Engine with the given routes
    engine = EcoTrafficEngine(routes)

    # Process the routes
    engine.store_routes_graph()
    # Get the routes information (by micro segments)
    return engine.get_routes_information()


def estimate_consumption_routes(routes, routes_information, vehicle):
    all_estimations = []
    # TODO check if index is the same for route and routes_information
    #  as it is retrieved afterwards it can be different
    # Create a route class with each route
    for i, route_information in enumerate(routes_information):
        # Process route to encode it
        processed_route = [(item.lat, item.lon) for item in routes[i]['segments']]

        encoded_route = polyline.encode(processed_route, 6)

        route = PathModel(segment_start_point=route_information['start_points'],
                          speed_limit_km_h=route_information['max_speeds'],
                          slope=route_information['slopes'])

        # Initialize vehicle movement object
        speed_profile = SpeedProfile(vehicle=vehicle, route=route)

        # Estimate the speed profile
        speed_profile.estimate_speed_profile()

        # Calculate acceleration
        speed_profile.calculate_acceleration()

        # Calculate resistances
        speed_profile.calculate_resistances()

        # Calculate slopes
        speed_profile.calculate_gravitational_resistances()

        # Estimate power consumption
        power_estimator = PowerEnergyEstimator(speed_profile)

        print(route)
        print(speed_profile.time)

        power_estimator.estimate_power_consumption(electric=vehicle.motor_type == 'ELECTRIC')

        # TODO how to calculate the elapsed time

        # Encode polyline using OpenStreetMap Algorithm
        all_estimations.append({'energy_consumption': f'{power_estimator.consumption[-1]}',
                                'distance': route.total_distance,
                                'time': -1,
                                'route': fr"{encoded_route}"})

    return all_estimations
