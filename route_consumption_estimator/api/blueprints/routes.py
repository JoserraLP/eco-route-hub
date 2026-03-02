from flask import Blueprint, request

from route_consumption_estimator.core.constants import DEFAULT_USER_ROUTE_ADDITIONAL_MASS
from route_consumption_estimator.api.security import api_required
from route_consumption_estimator.core.core import Core

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

    core = Core(vehicle_id, additional_mass)

    routes = core.execute_route_estimation_workflow(coordinates)

    return routes


@routes_bp.route('/routes/performed_route', methods=['POST'])
@api_required
def calculate_performed_route_metrics():
    data = request.get_json(force=True)

    # Get Vehicle
    vehicle_id = data['VehicleID']

    # Get additional mass
    additional_mass = data['AdditionalMass'] if 'AdditionalMass' in data else None

    core = Core(vehicle_id, additional_mass)

    speeds, heights = core.smooth_sensor_data(data['Speeds'], data['Heights'])

    times = data['Times']  # Represented as difference of time seconds between measurements

    # Performed route real metrics
    performed_route_metrics = core.execute_route_real_consumption_workflow(vehicle_id,
                                                                           additional_mass,
                                                                           heights,
                                                                           speeds,
                                                                           times)[0]

    # Performed route prior estimation
    # Get performed route polyline
    performed_route_polyline = data['RoutePolyline']
    performed_route_information = core.process_polyline_route(performed_route_polyline)

    # Calculate performed route estimated consumption based on maximum speeds
    performed_route_estimated_metrics = core.estimate_consumption_routes(routes_information=performed_route_information,
                                                                         routes=performed_route_information)[0]
    # Rename keys
    performed_route_estimated_metrics = {'PerformedRouteEstimatedConsumption':
                                             performed_route_estimated_metrics['EnergyConsumption'],
                                         'PerformedRouteEstimatedDistance':
                                             performed_route_estimated_metrics['Distance'],
                                         'PerformedRouteEstimatedTime': performed_route_estimated_metrics['Time']}

    return {**performed_route_metrics, **performed_route_estimated_metrics}
