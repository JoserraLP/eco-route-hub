"""
Benchmarking route handlers.

Provides RESTful API endpoints to execute benchmarking calculations across 
multiple consumption estimation models given specified coordinates, vehicle, 
and load parameters.
"""

from typing import Any, Dict, List, Tuple, Union
from flask import Blueprint, Response, current_app, jsonify, request

from route_consumption_estimator.app.security import api_required
from route_consumption_estimator.app.utils import convert_keys
from route_consumption_estimator.core.core import Core

# Blueprint definition for benchmarking operations
benchmarking_bp = Blueprint('benchmarking', __name__)


@benchmarking_bp.route('/benchmarking', methods=['GET'])
@api_required
def benchmarking() -> Tuple[Response, int]:
    """
    Execute a benchmarking workflow to compare route consumption models.

    Parses origin, destination, vehicle configuration, and optional intermediate 
    waypoints, executes the benchmarking calculations, converts output keys 
    to camelCase, and filters attributes according to system configuration settings.

    Query Parameters:
        source (str): Mandatory origin coordinates in LAT,LON format.
        destination (str): Mandatory destination coordinates in LAT,LON format.
        models (str, optional): Comma-separated list of model names to benchmark.
        inner_coords (str, optional): Intermediate waypoint coordinates in LAT,LON format.
        vehicle_id (str, optional): Target vehicle identifier.
        additional_mass (float, optional): Additional load mass in kg. 
            Defaults to default passenger mass from system config.

    Returns:
        Tuple[Response, int]: JSON list of filtered benchmarking results and HTTP 200,
                              or error response with HTTP status 400 or 500.
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

    # Parse optional parameters
    models_param = request.args.get('models', '')
    models = [m.strip() for m in models_param.split(',') if m.strip()]
    inner_coords = request.args.get('inner_coords', '')
    vehicle_id = request.args.get('vehicle_id', '')

    # Safely handle numeric conversion for additional_mass
    raw_mass = request.args.get('additional_mass')
    if raw_mass is not None and raw_mass != '':
        try:
            additional_mass: Union[float, str] = float(raw_mass)
        except ValueError:
            return jsonify({'message': 'Invalid numeric value for additional_mass'}), 400
    else:
        additional_mass = current_app_config.default_passenger_additional_mass

    # Format coordinate string for workflow execution
    coordinates = (
        f'{source};{inner_coords};{destination}'
        if inner_coords
        else f'{source};{destination}'
    )

    try:
        # Initialize Core engine and execute benchmarking calculations
        core = Core(registry, vehicle_id, additional_mass, models=models)
        routes = core.execute_benchmarking_workflow(coordinates)
    except Exception as err:
        return jsonify({
            'message': 'Error executing benchmarking workflow',
            'error': str(err)
        }), 500

    # Convert keys to camelCase formatting
    output = convert_keys(routes)

    # Filter keys based on configured system output variables
    filtered_output: Dict = {
        'pipelinePreparationMs': output['pipelinePreparationMs'],
        'simulations': [
            {
                key: value
                for key, value in item.items()
                if key in current_app_config.output_variables and value
            }
            for item in output['simulations']
        ]}

    return jsonify(filtered_output), 200
