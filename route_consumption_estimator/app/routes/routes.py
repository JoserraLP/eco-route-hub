"""
Routes route handlers.

Provides RESTful API endpoints for estimating route consumption and calculating 
metrics for performed routes based on telemetry and polyline data.
"""

from typing import Tuple
from flask import Blueprint, Response, current_app, jsonify, request

from route_consumption_estimator.app.security import api_required
from route_consumption_estimator.core.core import Core

# Blueprint definition for route estimations and metrics
routes_bp = Blueprint('routes', __name__)


@routes_bp.route('/routes', methods=['GET'])
@api_required
def get_all_routes() -> Tuple[Response, int]:
    """
    Execute route estimation workflow for given coordinates.

    Calculates estimated routes and energy consumption based on origin, 
    destination, optional intermediate waypoints, vehicle selection, and mass.

    Query Parameters:
        source (str): Mandatory origin coordinates in LAT,LON format.
        destination (str): Mandatory destination coordinates in LAT,LON format.
        inner_coords (str, optional): Intermediate waypoint coordinates in LAT,LON format.
        vehicle_id (str, optional): Target vehicle identifier.
        additional_mass (float, optional): Additional load mass in kg.

    Returns:
        Tuple[Response, int]: JSON representation of estimated routes and HTTP 200,
                              or error response with HTTP 400 or 500.
    """
    current_app_config = current_app.config["APP_CONFIG"].system
    registry = current_app.config["PLUGIN_REGISTRY"]

    # Extract and validate required query parameters
    source = request.args.get('source')
    destination = request.args.get('destination')

    if not source or not destination:
        return jsonify({
            'message': 'Parameters "source" and "destination" are required'
        }), 400

    inner_coords = request.args.get('inner_coords', '')
    vehicle_id = request.args.get('vehicle_id', '')

    # Safely handle numeric conversion for additional_mass
    raw_mass = request.args.get('additional_mass')
    if raw_mass is not None and raw_mass != '':
        try:
            additional_mass = float(raw_mass)
        except ValueError:
            return jsonify({'message': 'Invalid numeric value for additional_mass'}), 400
    else:
        additional_mass = current_app_config.default_passenger_additional_mass

    # Format coordinate string
    coordinates = (
        f'{source};{inner_coords};{destination}'
        if inner_coords
        else f'{source};{destination}'
    )

    try:
        core = Core(registry, vehicle_id, additional_mass)
        routes = core.execute_route_estimation_workflow(coordinates)
    except Exception as err:
        return jsonify({
            'message': 'Error executing route estimation workflow',
            'error': str(err)
        }), 500

    return jsonify(routes), 200


@routes_bp.route('/routes/performed_route', methods=['POST'])
@api_required
def calculate_performed_route_metrics() -> Tuple[Response, int]:
    """
    Calculate real and estimated metrics for a performed route based on sensor telemetry.

    Processes speed, height, and time telemetry data along with the route polyline 
    to compute actual consumption metrics and compare them against prior estimates.

    Request Body (JSON):
        VehicleID (str): Mandatory vehicle identifier.
        Speeds (list): Mandatory list of measured speeds.
        Heights (list): Mandatory list of measured elevation values.
        Times (list): Mandatory list of elapsed time intervals (in seconds).
        RoutePolyline (str or dict): Mandatory route geometry/polyline data.
        AdditionalMass (float, optional): Additional vehicle load mass in kg.

    Returns:
        Tuple[Response, int]: JSON dictionary combining real and estimated route metrics,
                              or error response with HTTP 400 or 500.
    """
    data = request.get_json(silent=True) or {}

    # Validate mandatory payload keys
    required_keys = ['VehicleID', 'Speeds', 'Heights', 'Times', 'RoutePolyline']
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        return jsonify({
            'message': f'Missing required parameter(s): {", ".join(missing_keys)}'
        }), 400

    vehicle_id = data['VehicleID']
    registry = current_app.config["PLUGIN_REGISTRY"]
    additional_mass = data.get('AdditionalMass')

    try:
        core = Core(registry, vehicle_id, additional_mass)

        # Smooth telemetry data
        speeds, heights = core.smooth_sensor_data(data['Speeds'], data['Heights'])
        times = data['Times']

        # Calculate real performed route metrics
        performed_route_metrics = core.execute_route_real_consumption_workflow(
            vehicle_id,
            additional_mass,
            heights,
            speeds,
            times
        )[0]

        # Calculate prior estimated metrics based on polyline
        performed_route_polyline = data['RoutePolyline']
        performed_route_information = core.process_polyline_route(performed_route_polyline)

        performed_route_estimated_metrics = core.estimate_consumption_routes(
            routes_information=performed_route_information,
            routes=performed_route_information
        )[0]

        # Map and rename prior estimation key names
        formatted_estimates = {
            'PerformedRouteEstimatedConsumption': performed_route_estimated_metrics['EnergyConsumption'],
            'PerformedRouteEstimatedDistance': performed_route_estimated_metrics['Distance'],
            'PerformedRouteEstimatedTime': performed_route_estimated_metrics['Time']
        }

        response_data = {**performed_route_metrics, **formatted_estimates}
        return jsonify(response_data), 200

    except Exception as err:
        return jsonify({
            'message': 'Error processing performed route metrics',
            'error': str(err)
        }), 500
