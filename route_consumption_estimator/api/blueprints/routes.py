import polyline
from flask import Blueprint, request

from route_consumption_estimator.api.constants import DEFAULT_USER_ROUTE_ADDITIONAL_MASS
from route_consumption_estimator.api.models import Vehicle
from route_consumption_estimator.api.security import api_required
from route_consumption_estimator.api.utils import request_routes, process_route_information, \
    estimate_consumption_routes, calculate_real_consumption, evaluate_consumption, smoothing_process
from route_consumption_estimator.graph.models import Coords
from route_consumption_estimator.routers.utils import process_route
from route_consumption_estimator.vehicle.veh_model import VehicleModel

# routes blueprint
routes_bp = Blueprint('routes', __name__)


@routes_bp.route('/routes', methods=['GET'])
@api_required
def get_all_routes():
    # Coords are LAT,LON
    source = request.args.get('source')
    destination = request.args.get('destination')
    inner_coords = request.args.get('inner_coords', '')
    vehicle_id = request.args.get('vehicle_id', '')
    additional_mass = request.args.get('additional_mass', DEFAULT_USER_ROUTE_ADDITIONAL_MASS)

    coordinates = f'{source};{inner_coords};{destination}' if inner_coords else f'{source};{destination}'

    routes = request_routes(coordinates)

    if routes:

        routes_information = process_route_information(routes)

        # Get vehicle to simulate
        vehicle = Vehicle.query.get(vehicle_id)

        # Update the vehicle A value with the additional mass
        if additional_mass:
            vehicle.recalculate_a(int(additional_mass))

        # Create a vehicle using the simulator model
        simulator_vehicle = VehicleModel(total_veh_mass=int(vehicle.UnladenVehMass) + int(additional_mass),
                                         liters_conversion=float(vehicle.LitersConversion),
                                         p_max_kw=float(vehicle.PMaxKw),
                                         A=float(vehicle.A),
                                         B=float(vehicle.B),
                                         C=float(vehicle.C),
                                         motor_type=str(vehicle.MotorType))

        estimations = estimate_consumption_routes(routes, routes_information, simulator_vehicle)

        # Merge both routes and estimations
        routes_estimations = [{**x, **y} for x, y in zip(routes, estimations)]

        # print(routes_estimations)

        # Filter the route: Eco, Shortest and Fastest
        consumption_index = min(enumerate(routes_estimations), key=lambda x: x[1]['EnergyConsumption'])[0]
        distance_index = min(enumerate(routes_estimations), key=lambda x: x[1]['Distance'])[0]
        time_index = min(enumerate(routes_estimations), key=lambda x: x[1]['Time'])[0]

        # Define final routes
        final_routes = {
            'eco': estimations[consumption_index],
            'shortest': estimations[distance_index],
            'fastest': estimations[time_index]
        }
    else:
        # Define final routes
        final_routes = {}

    # f'ROUTES_INFO: {[(route["router_distance"], route["router_duration"]) for route in routes]}' \
    #            f'\n Estimations: {estimations} with elapsed time {time.time() - start_time}'

    return final_routes


@routes_bp.route('/routes/performed_route', methods=['POST'])
@api_required
def calculate_performed_route_metrics():
    data = request.get_json(force=True)

    # Get Vehicle
    vehicle_id = data['VehicleID']

    # Get additional mass
    additional_mass = data['AdditionalMass'] if 'AdditionalMass' in data else None

    # Also get the speeds, heights and times. Smooth them based on alpha
    # This is for km/h speeds, parse to m/s
    speeds = smoothing_process([item / 3.6 for item in data['Speeds']], alpha=0.3)

    heights = smoothing_process(data['Heights'], alpha=0.3)

    times = data['Times']  # Represented as difference of time seconds between measurements

    # Get vehicle to simulate
    vehicle = Vehicle.query.get(vehicle_id)

    # Update the vehicle A value with the additional mass
    if additional_mass:
        vehicle.recalculate_a(int(additional_mass))

    # Create a vehicle using the simulator model
    simulator_vehicle = VehicleModel(total_veh_mass=int(vehicle.UnladenVehMass) + int(additional_mass),
                                     liters_conversion=float(vehicle.LitersConversion),
                                     p_max_kw=float(vehicle.PMaxKw),
                                     A=float(vehicle.A),
                                     B=float(vehicle.B),
                                     C=float(vehicle.C),
                                     motor_type=str(vehicle.MotorType))

    # Calculate performed route real consumption based on input data
    performed_route_metrics, accelerations = calculate_real_consumption(speeds=speeds, heights=heights, times=times,
                                                                        vehicle=simulator_vehicle)

    # Rename keys
    performed_route_metrics = {'PerformedRouteConsumption': performed_route_metrics['EnergyConsumption'],
                               'PerformedRouteDistance': performed_route_metrics['Distance'],
                               'PerformedRouteTime': performed_route_metrics['Time']}

    evaluation = evaluate_consumption(speeds=speeds, accelerations=accelerations,
                                      total_length=performed_route_metrics['PerformedRouteDistance'],
                                      times=times)

    # Performed route estimation
    # Get performed route polyline
    performed_route_polyline = data['RoutePolyline']

    performed_route_coords = polyline.decode(performed_route_polyline, 6)

    # Parse polyline into list of coords
    performed_route_coords = [Coords(lat=item[0], lon=item[1]) for item in performed_route_coords]

    processed_performed_route = process_route(route_coordinates=performed_route_coords,
                                              common_source=performed_route_coords[0],
                                              common_target=performed_route_coords[-1])

    routes_information = process_route_information([processed_performed_route])

    # Create the list with the information
    performed_route_info = routes_information

    # Calculate performed route estimated consumption based on maximum speeds
    performed_route_estimated_metrics = estimate_consumption_routes(routes_information=performed_route_info,
                                                                    routes=performed_route_info,
                                                                    vehicle=simulator_vehicle)
    # Rename keys
    # Item 0 as it is a list
    performed_route_estimated_metrics = {'PerformedRouteEstimatedConsumption':
                                             performed_route_estimated_metrics[0]['EnergyConsumption'],
                                         'PerformedRouteEstimatedDistance':
                                             performed_route_estimated_metrics[0]['Distance'],
                                         'PerformedRouteEstimatedTime': performed_route_estimated_metrics[0]['Time']}

    return {**performed_route_metrics, **evaluation, **performed_route_estimated_metrics}
