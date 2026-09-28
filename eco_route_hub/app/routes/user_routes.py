"""
User routes route handlers and statistics calculations.

Provides RESTful API endpoints for managing user routes (retrieval, creation, 
and deletion) and automatically updating aggregated user performance statistics.
"""

from datetime import datetime
from typing import Tuple, Union
from flask import Blueprint, Response, current_app, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from eco_route_hub import db
from eco_route_hub.app.security import api_required
from eco_route_hub.domain.dao_models import UserRouteDAOSchema, UserRouteDAO

# Blueprint definition for user routes operations
user_routes_bp = Blueprint('user_routes', __name__)

# Schema initializations for serialization and validation
user_route_schema = UserRouteDAOSchema()
user_routes_schema = UserRouteDAOSchema(many=True)

REQUIRED_CREATE_KEYS = {
    "UserID", "UserVehicleID", "AdditionalMass", "SourceCoords",
    "DestinationCoords", "SelectedRoutePolyline", "SelectedRouteType",
    "SelectedRouteConsumption", "SelectedRouteTime", "SelectedRouteDistance",
    "PerformedRoutePolyline", "PerformedRouteConsumption", "PerformedRouteTime",
    "PerformedRouteDistance", "PerformedRouteEstimatedConsumption",
    "PerformedRouteEstimatedTime", "PerformedRouteEstimatedDistance",
    "NumStopsKm", "SpeedVariationNum", "DrivingAggressiveness"
}


@user_routes_bp.route('/user_routes', methods=['GET'])
@api_required
def get_user_routes() -> Tuple[Response, int]:
    """
    Retrieve user routes from the database.

    Supports fetching the 5 most recent routes for a specific user ID, 
    or fetching all stored routes if no filter is provided.

    Query Parameters:
        user (str, optional): Target user identifier to filter routes.

    Returns:
        Tuple[Response, int]: JSON list of serialized user routes and HTTP status 200.
    """
    user = request.args.get('user', '')

    if user:
        # Retrieve the 5 most recent routes for the specified user
        user_routes = (
            UserRouteDAO.query
            .filter_by(UserID=user)
            .order_by(UserRouteDAO.RecordDate.desc())
            .limit(5)
            .all()
        )
    else:
        # Retrieve all user routes
        user_routes = UserRouteDAO.query.all()

    result = user_routes_schema.dump(user_routes)
    return jsonify(result), 200


@user_routes_bp.route('/user_routes', methods=['POST'])
@api_required
def create_user_route() -> Tuple[Response, int]:
    """
    Create a new user route entry and trigger user statistics recalculation.

    Validates that all required route execution fields are provided in the payload, 
    persists the route record, and updates aggregated performance metrics for the user.

    Request Body (JSON):
        Mandatory keys specified in REQUIRED_CREATE_KEYS.

    Returns:
        Tuple[Response, int]: JSON serialized created user route with HTTP 201 Created, 
                              or error response with HTTP status 400 or 500.
    """
    current_app_config = current_app.config["APP_CONFIG"].system
    data = request.get_json(silent=True) or {}

    # Validate mandatory payload keys
    missing_keys = REQUIRED_CREATE_KEYS - set(data.keys())
    if missing_keys:
        return jsonify({
            'message': f'Missing required parameters: {", ".join(sorted(missing_keys))}'
        }), 400

    now = datetime.now()

    # Instantiate new user route entity
    user_route = UserRouteDAO(
        UserID=data.get('UserID'),
        UserVehicleID=data.get('UserVehicleID'),
        AdditionalMass=data.get('AdditionalMass', current_app_config.default_passenger_additional_mass),
        SourceCoords=data.get('SourceCoords'),
        DestinationCoords=data.get('DestinationCoords'),
        SelectedRoutePolyline=data.get('SelectedRoutePolyline'),
        SelectedRouteType=data.get('SelectedRouteType'),
        SelectedRouteConsumption=data.get('SelectedRouteConsumption'),
        SelectedRouteTime=data.get('SelectedRouteTime'),
        SelectedRouteDistance=data.get('SelectedRouteDistance'),
        PerformedRoutePolyline=data.get('PerformedRoutePolyline'),
        PerformedRouteConsumption=data.get('PerformedRouteConsumption'),
        PerformedRouteTime=data.get('PerformedRouteTime'),
        PerformedRouteDistance=data.get('PerformedRouteDistance'),
        PerformedRouteEstimatedConsumption=data.get('PerformedRouteEstimatedConsumption'),
        PerformedRouteEstimatedTime=data.get('PerformedRouteEstimatedTime'),
        PerformedRouteEstimatedDistance=data.get('PerformedRouteEstimatedDistance'),
        NumStopsKm=data.get('NumStopsKm'),
        SpeedVariationNum=data.get('SpeedVariationNum'),
        DrivingAggressiveness=data.get('DrivingAggressiveness'),
        RecordDate=now.strftime('%Y-%m-%d %H:%M:%S')
    )

    try:
        db.session.add(user_route)
        db.session.commit()

        # Recalculate user statistics following route addition
        recalculate_user_stats(data['UserID'])

    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({'message': 'Database error occurred while saving user route'}), 500
    except Exception as err:
        db.session.rollback()
        return jsonify({
            'message': 'Error processing route creation or statistics recalculation',
            'error': str(err)
        }), 500

    result = user_route_schema.dump(user_route)
    return jsonify(result), 201


def recalculate_user_stats(user_id: str) -> None:
    """
    Recalculate aggregated performance and driving statistics for a given user.

    Computes consumption savings, eco-friendly driving proportions, and 
    overall driving rating across all stored routes for the user.

    Args:
        user_id (str): Target user identifier.
    """
    user_routes = UserRouteDAO.query.filter_by(UserID=user_id).all()
    if not user_routes:
        return

    # Accumulator variables
    total_estimated_consumption = 0.0
    total_real_consumption = 0.0
    eco_time = 0.0
    total_time = 0.0
    eco_distance = 0.0
    total_distance = 0.0
    eco_routes_num = 0
    drive_ratings = []

    # Process metrics directly from ORM instances without Marshmallow overhead
    for route in user_routes:
        est_cons = float(route.PerformedRouteEstimatedConsumption or 0)
        real_cons = float(route.PerformedRouteConsumption or 0)
        route_time = float(route.PerformedRouteTime or 0)
        route_dist = float(route.PerformedRouteDistance or 0)

        total_estimated_consumption += est_cons
        total_real_consumption += real_cons
        total_time += route_time
        total_distance += route_dist

        if route.SelectedRouteType == 'ECO' and str(route.SelectedRoutePolyline) != 'null':
            eco_time += route_time
            eco_distance += route_dist
            eco_routes_num += 1

        speed_var = float(route.SpeedVariationNum or 0)
        aggressiveness = float(route.DrivingAggressiveness or 0)
        drive_ratings.append((speed_var + aggressiveness) / 2.0)

    # Query target user stats using modern SQLAlchemy getter
    user_stats = db.session.get(UserStatsDAO, user_id)
    if not user_stats:
        return

    # Safe divisions to prevent ZeroDivisionError
    max_consumption = max(total_estimated_consumption, total_real_consumption)
    user_stats.ConsumptionSaving = (
        100.0 * (total_estimated_consumption - total_real_consumption) / max_consumption
        if max_consumption > 0 else 0.0
    )

    user_stats.EcoTime = (100.0 * eco_time / total_time) if total_time > 0 else 0.0
    user_stats.EcoDistance = (100.0 * eco_distance / total_distance) if total_distance > 0 else 0.0

    num_routes = len(user_routes)
    user_stats.EcoRoutesNum = (100.0 * eco_routes_num / num_routes) if num_routes > 0 else 0.0
    user_stats.DriveRating = (sum(drive_ratings) / len(drive_ratings)) if drive_ratings else 0.0

    db.session.commit()


@user_routes_bp.route('/user_routes', methods=['DELETE'])
@api_required
def delete_user_route() -> Union[Tuple[Response, int], Tuple[str, int]]:
    """
    Delete a user route record by its unique ID.

    Query Parameters:
        user_route_id (str): Mandatory user route identifier to delete.

    Returns:
        Union[Tuple[Response, int], Tuple[str, int]]: Empty response with HTTP 204 No Content on success, 
                                                      HTTP 400 Bad Request if param missing, 
                                                      HTTP 404 Not Found if record missing, 
                                                      or HTTP 500 on database failure.
    """
    user_route_id = request.args.get('user_route_id', '')

    # Missing query parameter is a client bad request (400)
    if not user_route_id:
        return jsonify({'message': 'Parameter user_route_id is required'}), 400

    # Retrieve record using modern SQLAlchemy syntax
    user_route = db.session.get(UserRouteDAO, user_route_id)

    if user_route is None:
        return jsonify({'message': 'User route not found'}), 404

    try:
        db.session.delete(user_route)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({'message': 'Database error occurred while deleting user route'}), 500

    return '', 204
