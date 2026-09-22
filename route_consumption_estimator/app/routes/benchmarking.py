from flask import Blueprint, request, current_app

from route_consumption_estimator.app import convert_keys
from route_consumption_estimator.app.security import api_required
from route_consumption_estimator.core.core import Core

# benchmarking blueprint
benchmarking_bp = Blueprint('benchmarking', __name__)


@benchmarking_bp.route('/benchmarking', methods=['GET'])
@api_required
def benchmarking():
    current_app_config = current_app.config["APP_CONFIG"].system
    registry = current_app.config["PLUGIN_REGISTRY"]
    # Coords are LAT,LON
    source = request.args.get('source')
    destination = request.args.get('destination')
    models = request.args.get('models', '')
    models = [model.strip() for model in models.split(',') if model.strip()]
    inner_coords = request.args.get('inner_coords', '')
    vehicle_id = request.args.get('vehicle_id', '')
    additional_mass = request.args.get('additional_mass', current_app_config.default_passenger_additional_mass)

    coordinates = f'{source};{inner_coords};{destination}' if inner_coords else f'{source};{destination}'

    core = Core(registry, vehicle_id, additional_mass, models=models)

    routes = core.execute_benchmarking_workflow(coordinates)

    output = convert_keys(routes)

    filtered_output = [
        {
            key: value
            for key, value in item.items()
            if key in current_app_config.output_variables and value
        }
        for item in output
    ]

    return filtered_output
