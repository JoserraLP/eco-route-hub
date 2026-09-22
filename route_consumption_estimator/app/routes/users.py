"""
User management route handlers.

Provides RESTful API endpoints for managing user accounts, including listing, 
creating, updating, and deleting user records.
"""

from typing import Tuple, Union
from flask import Blueprint, Response, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from route_consumption_estimator import db
from route_consumption_estimator.app.security import api_required
from route_consumption_estimator.domain.dao_models import UserDAOSchema, UserDAO

# Blueprint definition for user operations
users_bp = Blueprint('users', __name__)

# Schema initializations for serialization and validation
user_schema = UserDAOSchema()
users_schema = UserDAOSchema(many=True)

REQUIRED_CREATE_KEYS = {'Name', 'Email', 'Password'}


@users_bp.route('/users', methods=['GET'])
@api_required
def get_users() -> Tuple[Response, int]:
    """
    Retrieve user accounts from the database.

    Supports filtering users by email address or fetching all user records.

    Query Parameters:
        email (str, optional): Email address to filter users.

    Returns:
        Tuple[Response, int]: JSON list of serialized users and HTTP status 200.
    """
    email = request.args.get('email', '')

    if email:
        # Filter users by email
        users = UserDAO.query.filter_by(Email=email).all()
    else:
        # Retrieve all users
        users = UserDAO.query.all()

    result = users_schema.dump(users)
    return jsonify(result), 200


@users_bp.route('/users', methods=['POST'])
@api_required
def create_user() -> Tuple[Response, int]:
    """
    Create a new user account.

    Validates mandatory payload parameters (Name, Email, Password), verifies 
    email uniqueness, persists the user entity, and returns the created record.

    Request Body (JSON):
        Name (str): Mandatory user full name.
        Email (str): Mandatory user unique email address.
        Password (str): Mandatory user password.
        BirthDate (str, optional): User birth date string.
        Gender (str, optional): User gender.
        DrivingLicenseYear (int, optional): Year driving license was obtained.

    Returns:
        Tuple[Response, int]: JSON serialized created user with HTTP 201 Created, 
                              or error response with HTTP status 400 or 500.
    """
    data = request.get_json(silent=True) or {}

    # Validate mandatory payload keys
    missing_keys = REQUIRED_CREATE_KEYS - set(data.keys())
    if missing_keys:
        return jsonify({
            'message': f'Missing required parameter(s): {", ".join(sorted(missing_keys))}'
        }), 400

    # Solved Critical Bug: .filter_by(...) returns a Query object, which evaluates as True in Python.
    # Added .first() to check if a user with this email actually exists.
    existing_user = UserDAO.query.filter_by(Email=data['Email']).first()
    if existing_user is not None:
        return jsonify({'message': 'Email already used. Please select another'}), 400

    # Instantiate new user entity
    user = UserDAO(
        Name=data.get('Name'),
        Email=data.get('Email'),
        Password=data.get('Password'),
        BirthDate=data.get('BirthDate'),
        Gender=data.get('Gender'),
        DrivingLicenseYear=data.get('DrivingLicenseYear')
    )

    try:
        db.session.add(user)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({'message': 'Database error occurred while creating user'}), 500

    result = user_schema.dump(user)
    return jsonify(result), 201


@users_bp.route('/users', methods=['PUT'])
@api_required
def update_user() -> Tuple[Response, int]:
    """
    Update attributes of an existing user account.

    Request Body (JSON):
        UserID (str): Mandatory target user identifier.
        Name (str, optional): Updated user name.
        Email (str, optional): Updated user email.
        Password (str, optional): Updated user password.
        BirthDate (str, optional): Updated birth date.
        Gender (str, optional): Updated gender.
        DrivingLicenseYear (int, optional): Updated driving license year.

    Returns:
        Tuple[Response, int]: JSON serialized updated user with HTTP 200 OK, 
                              or error response with HTTP status 400, 404, or 500.
    """
    data = request.get_json(silent=True) or {}
    user_id = data.get('UserID')

    # Missing UserID is a client bad request (400)
    if not user_id:
        return jsonify({'message': 'Parameter UserID is required in JSON body'}), 400

    # Retrieve record using modern SQLAlchemy syntax
    user = db.session.get(UserDAO, user_id)

    if user is None:
        return jsonify({'message': 'User not found'}), 404

    # Partially update attributes if provided in payload
    user.Name = data.get('Name', user.Name)
    user.Email = data.get('Email', user.Email)
    user.Password = data.get('Password', user.Password)
    user.BirthDate = data.get('BirthDate', user.BirthDate)
    user.Gender = data.get('Gender', user.Gender)
    user.DrivingLicenseYear = data.get('DrivingLicenseYear', user.DrivingLicenseYear)

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({'message': 'Database error occurred while updating user'}), 500

    result = user_schema.dump(user)
    return jsonify(result), 200


@users_bp.route('/users', methods=['DELETE'])
@api_required
def delete_user() -> Union[Tuple[Response, int], Tuple[str, int]]:
    """
    Delete a user account by unique user ID.

    Query Parameters:
        user_id (str): Mandatory target user identifier to delete.

    Returns:
        Union[Tuple[Response, int], Tuple[str, int]]: Empty response with HTTP 204 No Content on success, 
                                                      HTTP 400 Bad Request if param missing, 
                                                      HTTP 404 Not Found if record missing, 
                                                      or HTTP 500 on database failure.
    """
    user_id = request.args.get('user_id', '')

    # Missing query parameter is a client bad request (400)
    if not user_id:
        return jsonify({'message': 'Parameter user_id is required'}), 400

    # Retrieve record using modern SQLAlchemy syntax
    user = db.session.get(UserDAO, user_id)

    if user is None:
        return jsonify({'message': 'User not found'}), 404

    try:
        db.session.delete(user)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({'message': 'Database error occurred while deleting user'}), 500

    return '', 204
