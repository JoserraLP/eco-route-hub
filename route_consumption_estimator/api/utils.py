import json

import polyline

from route_consumption_estimator.engine.route_engine import EcoTrafficEngine
from route_consumption_estimator.engine.utils import calculate_distances, calculate_slopes
from route_consumption_estimator.estimator.estimator import get_routes_graphhopper, get_routes_osrm, get_routes_ors
from route_consumption_estimator.graph.models import Coords
from route_consumption_estimator.path.path_model import PathModel
from route_consumption_estimator.vehicle.constants import POWER_PERCENTAGE, ACC_LIMIT_PROPORTION, CX, RO, GRAVITY, \
    AREA_FACTOR, ENGINE_PERFORMANCE
from route_consumption_estimator.vehicle.power_energy import PowerEnergyEstimator
from route_consumption_estimator.vehicle.speed_profile import SpeedProfile
from route_consumption_estimator.vehicle.veh_model import VehicleModel
from route_consumption_estimator.visualization.utils import show_graph


def load_all_vehicles(vehicles_dir):
    with open(vehicles_dir) as f:
        all_vehicles_data = json.load(f)

    return all_vehicles_data


def request_routes(coordinates: str):
    route_coordinates = [Coords(lat=float(coordinates.split(',')[0]), lon=float(coordinates.split(',')[1]))
                         for coordinates in coordinates.split(';')]

    # Define source and target to be the same over all routes
    source = route_coordinates[0]
    target = route_coordinates[-1]

    routes = get_routes_graphhopper(route_coordinates, common_source=source, common_target=target) + \
             get_routes_osrm(route_coordinates, common_source=source, common_target=target) + \
             get_routes_ors(route_coordinates, common_source=source, common_target=target)

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

        power_estimator.estimate_power_consumption(electric=vehicle.motor_type == 'ELECTRIC')

        # Encode polyline using OpenStreetMap Algorithm
        all_estimations.append({'energy_consumption': f'{power_estimator.consumption[-1]}',
                                'distance': route.total_distance,
                                'time': speed_profile.time[-1],
                                'route': fr"{encoded_route}"})

    return all_estimations


def calculate_real_consumption(heights, speeds, times, vehicle: VehicleModel):
    # Create a path model with the input data
    # Create the segment start point using the speed and the times
    segment_start_point = calculate_distances(speeds, times)

    slopes = calculate_slopes(heights=heights, speeds=speeds, times=times)

    route = PathModel(segment_start_point=segment_start_point,
                      slope=slopes, speed_limit_km_h=speeds)

    # Initialize vehicle movement object
    speed_profile = SpeedProfile(vehicle=vehicle, route=route)

    # Store the real speed profile, times and slope_t
    speed_profile.segment_length = segment_start_point
    speed_profile.speed_m_s = speeds
    speed_profile.time = times
    speed_profile.slope_t = slopes

    # Calculate acceleration
    speed_profile.calculate_acceleration()

    # Calculate resistances
    speed_profile.calculate_resistances()

    # Calculate slopes
    speed_profile.calculate_gravitational_resistances()

    # Estimate power consumption
    power_estimator = PowerEnergyEstimator(speed_profile)
    # electric=vehicle.motor_type == 'ELECTRIC'
    power_estimator.estimate_power_consumption()

    return {'energy_consumption': power_estimator.consumption[-1],
            'distance': segment_start_point[-1],
            'time': speed_profile.time[-1]}, speed_profile.acceleration


def evaluate_consumption(speeds, accelerations, total_length):
    # Initialize variables
    stops = 0
    lower_threshold = 0.1
    greater_threshold = 5
    num_acceleration_lower_threshold = 0
    num_acceleration_greater_threshold = 0

    # Iterate over the speeds
    for i in range(1, len(speeds)):
        # If the speed is lower than 3 km/h (0.8333333  m/s), increment the stops counter
        if speeds[i - 1] > 0.8333333 > speeds[i] > 0:
            stops += 1

        # Calculate the acceleration and add it to the list
        # acceleration = abs((speeds[i] - speeds[i - 1]) / (times[i] - times[i - 1]))
        # acceleration_list.append(acceleration)

        # Count number of times the acceleration is greater than thresholds
        if abs(accelerations[i]) > lower_threshold:
            num_acceleration_lower_threshold += 1
        if abs(accelerations[i]) > greater_threshold:
            num_acceleration_greater_threshold += 1

    stops_per_km = stops / (total_length / 1000)  # Parse to km
    percentage_acceleration_lower_threshold = num_acceleration_lower_threshold / len(accelerations)
    percentage_acceleration_greater_threshold = num_acceleration_greater_threshold / len(accelerations)

    # Print the results
    """
    print(
        f"Number of stops (where the speed is lower than 3km/h): {stops} ({stops_per_km} per km) of a total of {len(speeds)}")
    print(f"% of time acceleration greater than {lower_threshold}: {percentage_acceleration_lower_threshold}")
    print(f"% of time acceleration greater than {greater_threshold}: {percentage_acceleration_greater_threshold}")
    """

    total_score = {'num_stops_per_km': get_num_stops_per_km_score(stops_per_km),
                   'acceleration_lower_threshold': get_acceleration_lower_threshold_score(
                       percentage_acceleration_lower_threshold),
                   'acceleration_greater_threshold': get_acceleration_greater_threshold_score(
                       percentage_acceleration_greater_threshold)
                   }
    return total_score


def get_num_stops_per_km_score(value):
    if value > 1:
        return 1  # 'Manifiestamente mejorable'
    elif 1 <= value < 0.75:
        return 2  # 'Mejorable'
    elif 0.75 <= value < 0.50:
        return 3  # 'Aceptable'
    elif 0.5 <= value < 0.25:
        return 4  # 'Bien'
    else:
        return 5  # 'Muy bien'


def get_acceleration_lower_threshold_score(value):
    if value > 0.60:
        return 1  # 'Manifiestamente mejorable'
    elif 0.60 <= value < 0.40:
        return 2  # 'Mejorable'
    elif 0.40 <= value < 0.20:
        return 3  # 'Aceptable'
    elif 0.20 <= value < 0.10:
        return 4  # 'Bien'
    else:
        return 5  # 'Muy bien'


def get_acceleration_greater_threshold_score(value):
    if value > 0.05:
        return 1  # 'Manifiestamente mejorable'
    elif 0.05 <= value < 0.03:
        return 2  # 'Mejorable'
    elif 0.03 <= value < 0.01:
        return 3  # 'Aceptable'
    elif 0.01 <= value < 0.005:
        return 4  # 'Bien'
    else:
        return 5  # 'Muy bien'
