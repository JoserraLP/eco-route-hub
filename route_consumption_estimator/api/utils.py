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


def load_vehicle(all_vehicles_data: dict, vehicle_id: str):
    if vehicle_id in all_vehicles_data:
        vehicle_data = all_vehicles_data[vehicle_id]

        # Get all data with default values
        motor_type = vehicle_data.get('motor_type', 'diesel')  # Motor type
        unladen_veh_mass = vehicle_data.get('unladen_veh_mass', 0)  # Unladen mass of vehicle
        load_veh_mass = vehicle_data.get('load_veh_mass', 0)  # Load mass on the vehicle (not total)
        total_veh_mass = vehicle_data.get('total_veh_mass', 0)  # Total mass of load vehicle
        resistance_factor = vehicle_data.get('resistance_factor', 0.015)  # Resistance factor to advance
        p_max_kw = vehicle_data.get('p_max_kw', 81)  # Maximum potency on Kw
        kwh_per_l = vehicle_data.get('consumption_kwh_100km', 9.2)  # Consumption of fuel liters per Kw/h
        cx = vehicle_data.get('cx', 0)  # Aerodynamic coefficient
        A = vehicle_data.get('A', 195)  # A
        C = vehicle_data.get('C', 0.033)  # C
        long = vehicle_data.get('long', 0)  # Longitude of the vehicle
        height = vehicle_data.get('height', 0)  # Latitude of the vehicle
        width = vehicle_data.get('width', 0)  # Width of the vehicle
        frontal_area_m = vehicle_data.get('frontal_area_m', 0)
        # Frontal area in meters, if None is calculated with previous value

        gamma = 1.05

        vehicle = VehicleModel(unladen_veh_mass=unladen_veh_mass, load_veh_mass=load_veh_mass,
                               total_mass=total_veh_mass, gamma=gamma,
                               resistance_advance=resistance_factor, p_max_kw=p_max_kw,
                               kwh_per_l=kwh_per_l, auxiliar_consumption_l_h=0.6, height=height,
                               width=width, area_factor=AREA_FACTOR, A=A, C=C, frontal_area_m=frontal_area_m)
    else:
        # Initialize default vehicle
        vehicle = VehicleModel(unladen_veh_mass=1130, load_veh_mass=150, gamma=1.05, resistance_advance=0.015,
                               p_max_kw=81, kwh_per_l=9.2, auxiliar_consumption_l_h=0.6, height=1.459, width=1.78,
                               area_factor=AREA_FACTOR, A=195, C=0.033, total_mass=0)
    return vehicle


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

        power_estimator.estimate_power_consumption()

        # Encode polyline using OpenStreetMap Algorithm
        all_estimations.append({'estimation': f'{power_estimator.consumption[-1]} liters',
                                'route': fr"{encoded_route}"})

        # FIXME On the other side encode the processed route by dividing it by 10 and round it to 6 decimal
        decoded_route = [(round(item[0] / 10, 6), round(item[1] / 10, 6)) for item in
                         polyline.decode(encoded_route)]

    return all_estimations
