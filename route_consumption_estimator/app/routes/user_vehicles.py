"""
User vehicles route handlers.

Provides RESTful API endpoints for managing vehicles associated with users, 
including listing/filtering vehicles, creating new user-vehicle associations, 
updating vehicle details, and removing records.
"""

from typing import Tuple, Union
from flask import Blueprint, Response, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from route_consumption_estimator import db
from route_consumption_estimator.app.security import api_required
from route_consumption_estimator.domain.dao_models import UserVehicleDAOSchema, UserVehicleDAO

# Blueprint definition for user vehicles management
user_vehicles_bp = Blueprint('user_vehicles', __name__)

# Schema initializations for serialization and validation
user_vehicle_schema = UserVehicleDAOSchema()
user_vehicles_schema = UserVehicleDAOSchema(many=True)


@user_vehicles_bp.route('/user_vehicles', methods=['GET'])
@api_required
def get_users_vehicles() -> Tuple[Response, int]:
    """
    Retrieve user vehicles based on query parameters.

    Supports querying all vehicles owned by a specific user, fetching a single 
    user-vehicle entry by its unique ID, or listing all recorded user vehicles.

    Query Parameters:
        user (str, optional): Target user ID to filter associated vehicles.
        user_vehicle_id (str, optional): Unique user vehicle identifier.

    Returns:
        Tuple[Response, int]: JSON list containing matching user vehicle records and HTTP status 200.
    """
    user = request.args.get('user', '')
    user_vehicle_id = request.args.get('user_vehicle_id', '')

    if user:
        # Query database for all vehicles tied to the specified user
        user_vehicles = UserVehicleDAO.query.filter_by(UserID=user).all()
    elif user_vehicle_id:
        # Solved NameError (id -> user_vehicle_id) and used modern session.get
        user_vehicle = db.session.get(UserVehicleDAO, user_vehicle_id)
        user_vehicles = [user_vehicle] if user_vehicle else []
    else:
        # Query database for all user vehicle records
        user_vehicles = UserVehicleDAO.query.all()

    result = user_vehicles_schema.dump(user_vehicles)
    return jsonify(result), 200


@user_vehicles_bp.route('/user_vehicles', methods=['POST'])
@api_required
def create_user_vehicle() -> Tuple[Response, int]:
    """
    Create a new user-vehicle association.

    Validates mandatory parameters (UserID and VehicleID), persists the record, 
    and returns the created user vehicle object.

    Request Body (JSON):
        UserID (str): Mandatory target user identifier.
        VehicleID (str): Mandatory vehicle template identifier.
        Age (int, optional): Vehicle age in years.
        KmUsed (float, optional): Total distance driven/mileage on vehicle.
        IsFav (bool, optional): Whether vehicle is marked as favorite.

    Returns:
        Tuple[Response, int]: JSON serialized created user vehicle with HTTP 201 Created, 
                              or error response with HTTP status 400 or 500.
    """
    data = request.get_json(silent=True) or {}

    # Validate mandatory payload parameters
    if 'UserID' not in data or 'VehicleID' not in data:
        return jsonify({'message': 'Missing required parameters: UserID and VehicleID'}), 400

    # Instantiate new user vehicle entity
    user_vehicle = UserVehicleDAO(
        UserID=data['UserID'],
        VehicleID=data['VehicleID'],
        Age=data.get('Age'),
        KmUsed=data.get('KmUsed'),
        IsFav=data.get('IsFav')
    )

    try:
        db.session.add(user_vehicle)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({'message': 'Database error occurred while creating user vehicle'}), 500

    result = user_vehicle_schema.dump(user_vehicle)
    return jsonify(result), 201


@user_vehicles_bp.route('/user_vehicles', methods=['PUT'])
@api_required
def update_user_vehicle() -> Tuple[Response, int]:
    """
    Update attributes for an existing user vehicle entry.

    Request Body (JSON):
        ID (str): Mandatory target user vehicle identifier.
        UserID (str, optional): Updated user owner ID.
        VehicleID (str, optional): Updated vehicle template ID.
        Age (int, optional): Updated vehicle age.
        KmUsed (float, optional): Updated vehicle mileage.
        IsFav (bool, optional): Updated favorite status.

    Returns:
        Tuple[Response, int]: JSON serialized updated user vehicle with HTTP 200 OK, 
                              or error response with HTTP status 400, 404, or 500.
    """
    data = request.get_json(silent=True) or {}
    user_vehicle_id = data.get('ID')

    # Missing ID is a bad request (400)
    if not user_vehicle_id:
        return jsonify({'message': 'Parameter ID is required in JSON body'}), 400

    # Retrieve record using modern SQLAlchemy syntax
    user_vehicle = db.session.get(UserVehicleDAO, user_vehicle_id)

    if user_vehicle is None:
        return jsonify({'message': 'User vehicle not found'}), 404

    # Partially update attributes if provided in payload
    user_vehicle.UserID = data.get('UserID', user_vehicle.UserID)
    user_vehicle.VehicleID = data.get('VehicleID', user_vehicle.VehicleID)
    user_vehicle.Age = data.get('Age', user_vehicle.Age)
    user_vehicle.KmUsed = data.get('KmUsed', user_vehicle.KmUsed)
    user_vehicle.IsFav = data.get('IsFav', user_vehicle.IsFav)

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({'message': 'Database error occurred while updating user vehicle'}), 500

    result = user_vehicle_schema.dump(user_vehicle)
    return jsonify(result), 200


@user_vehicles_bp.route('/user_vehicles', methods=['DELETE'])
@api_required
def delete_user_vehicle() -> Union[Tuple[Response, int], Tuple[str, int]]:
    """
    Delete a user vehicle record by its unique identifier.

    Query Parameters:
        user_vehicle_id (str): Mandatory ID of the user vehicle to delete.

    Returns:
        Union[Tuple[Response, int], Tuple[str, int]]: Empty response with HTTP 204 No Content on success, 
                                                      HTTP 400 Bad Request if param missing, 
                                                      HTTP 404 Not Found if record missing, 
                                                      or HTTP 500 on database failure.
    """
    user_vehicle_id = request.args.get('user_vehicle_id', '')

    # Missing query parameter is a client bad request (400)
    if not user_vehicle_id:
        return jsonify({'message': 'Parameter user_vehicle_id is required'}), 400

    # Retrieve record using modern SQLAlchemy syntax
    user_vehicle = db.session.get(UserVehicleDAO, user_vehicle_id)

    if user_vehicle is None:
        return jsonify({'message': 'User vehicle not found'}), 404

    try:
        db.session.delete(user_vehicle)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({'message': 'Database error occurred while deleting user vehicle'}), 500

    return '', 204
