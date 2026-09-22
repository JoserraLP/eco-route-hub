"""
User statistics route handlers.

Provides RESTful API endpoints for managing aggregated user performance statistics, 
including listing/filtering statistics, manual creation, updates, and deletion.
"""

from typing import Tuple, Union
from flask import Blueprint, Response, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from route_consumption_estimator import db
from route_consumption_estimator.app.security import api_required
from route_consumption_estimator.domain.dao_models import UserStatsDAOSchema, UserStatsDAO

# Blueprint definition for user statistics operations
user_stats_bp = Blueprint('user_stats', __name__)

# Schema initializations for serialization and validation
user_stat_schema = UserStatsDAOSchema()
user_stats_schema = UserStatsDAOSchema(many=True)

REQUIRED_CREATE_KEYS = {
    'UserID', 'ConsumptionSaving', 'EcoTime', 'EcoDistance', 'EcoRoutesNum', 'DriveRating'
}


@user_stats_bp.route('/user_stats', methods=['GET'])
@api_required
def get_user_stats() -> Tuple[Response, int]:
    """
    Retrieve user performance statistics.

    Supports querying statistics for a specific user ID or fetching 
    all stored user statistics.

    Query Parameters:
        user (str, optional): Target user identifier to filter statistics.

    Returns:
        Tuple[Response, int]: JSON list containing matching user statistics and HTTP status 200.
    """
    user = request.args.get('user', '')

    if user:
        # Use modern db.session.get and filter out None if record does not exist
        user_stat = db.session.get(UserStatsDAO, user)
        user_stats = [user_stat] if user_stat else []
    else:
        # Query database for all user statistics
        user_stats = UserStatsDAO.query.all()

    result = user_stats_schema.dump(user_stats)
    return jsonify(result), 200


@user_stats_bp.route('/user_stats', methods=['POST'])
@api_required
def create_user_stats() -> Tuple[Response, int]:
    """
    Create a new user statistics record.

    Validates mandatory metrics fields, persists the entity in the database, 
    and returns the created record.

    Request Body (JSON):
        UserID (str): Mandatory target user identifier.
        ConsumptionSaving (float): Percentage of fuel or energy saved.
        EcoTime (float): Percentage of time driven in ECO mode.
        EcoDistance (float): Percentage of distance driven in ECO mode.
        EcoRoutesNum (float): Percentage of eco-friendly routes chosen.
        DriveRating (float): Overall driving score or aggressiveness rating.

    Returns:
        Tuple[Response, int]: JSON serialized created stats with HTTP 201 Created, 
                              or error response with HTTP status 400 or 500.
    """
    data = request.get_json(silent=True) or {}

    # Validate mandatory payload keys
    missing_keys = REQUIRED_CREATE_KEYS - set(data.keys())
    if missing_keys:
        return jsonify({
            'message': f'Missing required parameter(s): {", ".join(sorted(missing_keys))}'
        }), 400

    # Instantiate new user stats entity
    user_stat = UserStatsDAO(
        UserID=data['UserID'],
        ConsumptionSaving=data['ConsumptionSaving'],
        EcoTime=data['EcoTime'],
        EcoDistance=data['EcoDistance'],
        EcoRoutesNum=data['EcoRoutesNum'],
        DriveRating=data['DriveRating']
    )

    try:
        db.session.add(user_stat)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({'message': 'Database error occurred while creating user statistics'}), 500

    result = user_stat_schema.dump(user_stat)
    return jsonify(result), 201


@user_stats_bp.route('/user_stats', methods=['PUT'])
@api_required
def update_user_stats() -> Tuple[Response, int]:
    """
    Update performance statistics for an existing user.

    Request Body (JSON):
        UserID (str): Mandatory target user identifier.
        ConsumptionSaving (float, optional): Updated consumption saving percentage.
        EcoTime (float, optional): Updated ECO driving time percentage.
        EcoDistance (float, optional): Updated ECO distance percentage.
        EcoRoutesNum (float, optional): Updated percentage of ECO routes.
        DriveRating (float, optional): Updated driving score.

    Returns:
        Tuple[Response, int]: JSON serialized updated stats with HTTP 200 OK, 
                              or error response with HTTP status 400, 404, or 500.
    """
    data = request.get_json(silent=True) or {}
    user_id = data.get('UserID')

    # Missing UserID is a bad request (400)
    if not user_id:
        return jsonify({'message': 'Parameter UserID is required in JSON body'}), 400

    # Query target entity using modern SQLAlchemy syntax
    user_stat = db.session.get(UserStatsDAO, user_id)

    if user_stat is None:
        return jsonify({'message': 'User statistics record not found'}), 404

    # Partially update attributes if provided in payload
    user_stat.ConsumptionSaving = data.get('ConsumptionSaving', user_stat.ConsumptionSaving)
    user_stat.EcoTime = data.get('EcoTime', user_stat.EcoTime)
    user_stat.EcoDistance = data.get('EcoDistance', user_stat.EcoDistance)
    user_stat.EcoRoutesNum = data.get('EcoRoutesNum', user_stat.EcoRoutesNum)
    user_stat.DriveRating = data.get('DriveRating', user_stat.DriveRating)

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({'message': 'Database error occurred while updating user statistics'}), 500

    # Fix: Dump single entity using user_stat_schema instead of user_stats_schema (many=True)
    result = user_stat_schema.dump(user_stat)
    return jsonify(result), 200


@user_stats_bp.route('/user_stats', methods=['DELETE'])
@api_required
def delete_user_stats() -> Union[Tuple[Response, int], Tuple[str, int]]:
    """
    Delete user statistics record by user identifier.

    Query Parameters:
        user (str): Mandatory target user ID whose stats should be deleted.

    Returns:
        Union[Tuple[Response, int], Tuple[str, int]]: Empty response with HTTP 204 No Content on success, 
                                                      HTTP 400 Bad Request if param missing, 
                                                      HTTP 404 Not Found if record missing, 
                                                      or HTTP 500 on database failure.
    """
    user = request.args.get('user', '')

    # Missing query parameter is a client bad request (400)
    if not user:
        return jsonify({'message': 'Parameter user is required'}), 400

    # Query record using modern SQLAlchemy syntax
    user_stat = db.session.get(UserStatsDAO, user)

    if user_stat is None:
        return jsonify({'message': 'User statistics record not found'}), 404

    try:
        db.session.delete(user_stat)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({'message': 'Database error occurred while deleting user statistics'}), 500

    return '', 204
