import argparse
import json

from route_consumption_estimator.engine.route_engine import EcoTrafficEngine
from route_consumption_estimator.estimator.estimator import *
from route_consumption_estimator.estimator.utils import kmz_to_coordinates, get_kmz_filter
from route_consumption_estimator.experiments.utils import estimate_consumption_from_file
from route_consumption_estimator.graph.models import Coords
from route_consumption_estimator.path.path_model import PathModel
from route_consumption_estimator.vehicle.constants import AREA_FACTOR
from route_consumption_estimator.vehicle.power_energy import PowerEnergyEstimator
from route_consumption_estimator.vehicle.speed_profile import SpeedProfile
from route_consumption_estimator.vehicle.veh_model import VehicleModel
from route_consumption_estimator.visualization.plots import compare_consumption, show_consumption


def get_options():
    """
    Get options from the execution command

    :return: Arguments options
    """
    # Create the Argument Parser
    arg_parser = argparse.ArgumentParser(description='Route consumption estimator')

    # Define the arguments options
    arg_parser.add_argument('-C', '--coords', dest='coords', action='store', type=str,
                            help='define the input coords (lat, lon) for the route, divided with ";". '
                                 'First coordinates: sources. Intermediate coordinates: intermediate points. '
                                 'Last coordinates: destination.')
    arg_parser.add_argument('--vehicle-dir', dest='vehicle_dir', action='store', type=str,
                            help='Vehicle where there are stored the vehicles')
    arg_parser.add_argument('-v', '--vehicle', dest='VehicleID', action='store', type=str,
                            help='Vehicle identifier')

    # python estimator.py -C 43.5231781,-5.6276553;43.3828673,-5.8237067 --vehicle-dir ../../experiments_july/vehicles.json -v skoda

    # Define the arguments options
    kmz_group = arg_parser.add_argument_group("Parameters related to KMZ execution")
    kmz_group.add_argument('-d', '--dir', dest='dir', action='store', type=str,
                           help='define the root experiment folder')
    # Default should be: "../../experiments_november"
    kmz_group.add_argument('--city', dest='city', action='store', type=str,
                           help='define the city where the route experiments are stored')
    kmz_group.add_argument('--route', dest='route', action='store', type=int,
                           help='define the route number')

    # python estimator.py --vehicle-dir ../../experiments_november/vehicles.json -v volskwagen_golf_1.6_tdi -d ../../experiments_november --city madrid --route 1

    # Retrieve the arguments parsed
    args = arg_parser.parse_args()
    return args


if __name__ == "__main__":

    # Retrieve execution options (parameters)
    exec_options = get_options()

    route_coordinates, routes = [], []

    # Load KMZ
    if exec_options.dir:
        file_dir = f"{exec_options.dir}/routes_{exec_options.city}/Ruta {exec_options.route}.kmz"

        # Retrieve the coordinates from the LineString feature
        route_coordinates = kmz_to_coordinates(file_dir)

        filter_kmz = get_kmz_filter(exec_options.city, exec_options.route)

        route_coordinates = [route_coordinates[i] for i in range(len(route_coordinates)) if i % filter_kmz == 0]

        # For experiments, just use OSRM
        routes = get_routes_osrm(route_coordinates)

        # coordinates = [(coords.lon, coords.lat) for coords in routes[0]['segments']]
        # plot_points_on_map(coordinates)

    elif exec_options.coords:

        route_coordinates = [Coords(lat=float(coordinates.split(',')[0]), lon=float(coordinates.split(',')[1]))
                             for coordinates in exec_options.coords.split(';')
                             for coord in coordinates.split(',')]

        routes = get_routes_osrm(route_coordinates)

        # "Parameter 'alternative_routes' is incompatible with parameter '(number of waypoints > 2)'."}
        """
        routes = get_routes_graphhopper(route_coordinates) + get_routes_osrm(route_coordinates) + \
                 get_routes_ors(route_coordinates)
        """
    # Start Eco-Traffic Engine with the given routes
    engine = EcoTrafficEngine(routes)

    # Process the routes
    engine.store_routes_graph()

    # Empty
    if not engine.routes:
        exit("No routes")

    # Get the routes information (by micro segments)
    routes_information = engine.get_routes_information()

    # Create vehicle
    if exec_options.vehicle_dir and exec_options.vehicle_id:

        with open(exec_options.vehicle_dir) as f:
            all_vehicles_data = json.load(f)

        vehicle_data = all_vehicles_data[exec_options.vehicle_id]
        # Get all data with default values
        motor_type = vehicle_data.get('MotorType', 'diesel')  # Motor type
        unladen_veh_mass = vehicle_data.get('UnladenVehMass', 0)  # Unladen mass of vehicle
        load_veh_mass = vehicle_data.get('LoadVehMass', 0)  # Load mass on the vehicle (not total)
        total_veh_mass = vehicle_data.get('total_veh_mass', 0)  # Total mass of load vehicle
        resistance_factor = vehicle_data.get('ResistanceFactor', 0.015)  # Resistance factor to advance
        p_max_kw = vehicle_data.get('PMaxKw', 81)  # Maximum potency on Kw
        kwh_per_l = vehicle_data.get('consumption_kwh_100km', 9.2)  # Consumption of fuel liters per Kw/h
        cx = vehicle_data.get('cx', 0)  # Aerodynamic coefficient
        A = vehicle_data.get('A', 195)  # A
        C = vehicle_data.get('C', 0.033)  # C
        long = vehicle_data.get('long', 0)  # Longitude of the vehicle
        height = vehicle_data.get('Height', 0)  # Latitude of the vehicle
        width = vehicle_data.get('Width', 0)  # Width of the vehicle
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

    # Create A route class with each route
    for route_information in routes_information:
        route = PathModel(segment_start_point=route_information['start_points'],
                          speed_limit_km_h=route_information['max_speeds'],
                          slope=route_information['slopes'])

        # Initialize vehicle movement object
        speed_profile = SpeedProfile(vehicle=vehicle, route=route)

        # Estimate the speed profile
        speed_profile.estimate_speed_profile()

        # Get the speed profile on km/h
        speed_profile_value = [speed * 3.6 for speed in speed_profile.speed_m_s][:-1]

        # Calculate acceleration
        speed_profile.calculate_acceleration()

        # Calculate resistances
        speed_profile.calculate_resistances()

        # Calculate slopes
        speed_profile.calculate_gravitational_resistances()

        # Estimate power consumption
        power_estimator = PowerEnergyEstimator(speed_profile)

        power_estimator.estimate_power_consumption()

        show_consumption(power_estimator.consumption)

        if exec_options.coords == "43.5231781,-5.6276553;43.3828673,-5.8237067":
            # Compare with first result
            file = '../../experiments_july/consumption_files/resultado1'

            experiment_consumption = estimate_consumption_from_file(file, vehicle)

            compare_consumption(engine_based_consumption=power_estimator.consumption,
                                experiment_loaded_consumption=experiment_consumption)
