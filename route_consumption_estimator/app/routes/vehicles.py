"""
Vehicle catalog route handlers.

Provides RESTful API endpoints for querying, creating, and deleting 
vehicle specification entries used for route energy and fuel consumption estimations.
"""

from typing import Tuple, Union
from flask import Blueprint, Response, current_app, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from route_consumption_estimator import db
from route_consumption_estimator.app.security import api_required
from route_consumption_estimator.domain.constants import GRAVITY
from route_consumption_estimator.domain.dao_models import VehicleDAOSchema, VehicleDAO

# Blueprint definition for vehicle operations
vehicles_bp = Blueprint('vehicles', __name__)

# Schema initializations for serialization and validation
vehicle_schema = VehicleDAOSchema()
vehicles_schema = VehicleDAOSchema(many=True)

REQUIRED_CREATE_KEYS = {'Name', 'MotorType', 'UnladenVehMass', 'PMaxKw'}


@vehicles_bp.route('/vehicles', methods=['GET'])
@api_required
def get_vehicles() -> Tuple[Response, int]:
    """
    Retrieve vehicles from the database.

    Supports searching by name substring, fetching a specific vehicle by ID, 
    or retrieving all vehicle entries.

    Query Parameters:
        q (str, optional): Substring query to match against vehicle names.
        vehicle_id (str, optional): Unique vehicle identifier.

    Returns:
        Tuple[Response, int]: JSON list of matching vehicle records and HTTP status 200.
    """
    query = request.args.get('q', '')
    vehicle_id = request.args.get('vehicle_id', '')

    if query:
        # Solved Bug: Added .all() to execute query instead of returning a BaseQuery object
        vehicles = VehicleDAO.query.filter(VehicleDAO.Name.like(f'%{query}%')).all()
    elif vehicle_id:
        # Fetch single vehicle by ID using modern SQLAlchemy syntax
        vehicle = db.session.get(VehicleDAO, vehicle_id)
        vehicles = [vehicle] if vehicle else []
    else:
        # Retrieve all vehicle records
        vehicles = VehicleDAO.query.all()

    result = vehicles_schema.dump(vehicles)
    return jsonify(result), 200


@vehicles_bp.route('/vehicles', methods=['POST'])
@api_required
def create_vehicle() -> Tuple[Response, int]:
    """
    Create a new vehicle catalog entry with automatic physics parameter calculation.

    Validates mandatory vehicle specifications, calculates resistance coefficients 
    (A, B, C) and fuel conversion factors if not directly provided, and persists 
    the entity.

    Request Body (JSON):
        Name (str): Mandatory vehicle name/model description.
        MotorType (str): Mandatory powertrain type (e.g., 'Gasoline', 'Diesel', 'EV').
        UnladenVehMass (float): Mandatory unladen vehicle mass in kg.
        PMaxKw (float): Mandatory maximum engine power output in kW.
        ResistanceFactor (float, optional): Rolling resistance factor.
        Width (float, optional): Vehicle width in mm.
        Height (float, optional): Vehicle height in mm.
        FrontalArea (float, optional): Frontal surface area in m².
        Cx (float, optional): Aerodynamic drag coefficient.
        A (float, optional): Custom resistance coefficient A.
        B (float, optional): Custom resistance coefficient B.
        C (float, optional): Custom resistance coefficient C.
        LitersConversion (float, optional): Specific energy/fuel consumption conversion factor.
        Url (str, optional): External documentation link.
        ImageUrl (str, optional): Vehicle image resource URL.

    Returns:
        Tuple[Response, int]: JSON serialized created vehicle with HTTP 201 Created, 
                              or error response with HTTP status 400 or 500.
    """
    current_app_config = current_app.config["APP_CONFIG"].system
    data = request.get_json(silent=True) or {}

    # Validate mandatory payload keys
    missing_keys = REQUIRED_CREATE_KEYS - set(data.keys())
    if missing_keys:
        return jsonify({
            'message': f'Missing required parameter(s): {", ".join(sorted(missing_keys))}'
        }), 400

    unladen_mass = float(data.get('UnladenVehMass', 0.0))
    rf = data.get('ResistanceFactor', current_app_config.vehicle_default_rf)

    # Calculate resistance parameter A: ResistanceFactor * (UnladenVehMass + AdditionalMass) * GRAVITY
    a_param = data.get(
        'A',
        rf * (unladen_mass + current_app_config.default_passenger_additional_mass) * GRAVITY
    )

    # Resistance parameter B
    b_param = data.get('B', current_app_config.vehicle_default_b)

    # Calculate Frontal Area (Width & Height in mm converted to meters)
    width_m = data.get('Width', 0.0) / 1000.0
    height_m = data.get('Height', 0.0) / 1000.0
    computed_frontal_area = 0.85 * width_m * height_m
    frontal_area = data.get('FrontalArea', computed_frontal_area)

    # Calculate resistance parameter C: 0.5 * air_density * FrontalArea * Cx * (1/3.6)^2
    cx = data.get('Cx', current_app_config.vehicle_default_cx)
    c_param = data.get('C', 0.5 * 1.225 * frontal_area * cx * (1.0 / 3.6) ** 2)

    # Determine default liters conversion based on motor type
    motor_type = data.get('MotorType')
    liters_conversion = 0.0
    if motor_type == "Gasoline":
        liters_conversion = current_app_config.vehicle_default_gasoline_conversion
    elif motor_type == "Diesel":
        liters_conversion = current_app_config.vehicle_default_diesel_conversion

    # Instantiate new vehicle entity
    vehicle = VehicleDAO(
        Name=data.get('Name'),
        MotorType=motor_type,
        UnladenVehMass=unladen_mass,
        PMaxKw=data.get('PMaxKw'),
        LitersConversion=data.get('LitersConversion', liters_conversion),
        ResistanceFactor=rf,
        A=a_param,
        B=b_param,
        C=c_param,
        Url=data.get('Url', ''),
        ImageUrl=data.get('ImageUrl', '')
    )

    try:
        db.session.add(vehicle)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({'message': 'Database error occurred while creating vehicle'}), 500

    result = vehicle_schema.dump(vehicle)
    return jsonify(result), 201


@vehicles_bp.route('/vehicles', methods=['DELETE'])
@api_required
def delete_vehicle() -> Union[Tuple[Response, int], Tuple[str, int]]:
    """
    Delete a vehicle record by its unique identifier.

    Query Parameters:
        vehicle_id (str): Mandatory target vehicle ID to delete.

    Returns:
        Union[Tuple[Response, int], Tuple[str, int]]: Empty response with HTTP 204 No Content on success, 
                                                      HTTP 400 Bad Request if param missing, 
                                                      HTTP 404 Not Found if record missing, 
                                                      or HTTP 500 on database failure.
    """
    vehicle_id = request.args.get('vehicle_id', '')

    # Missing query parameter is a client bad request (400)
    if not vehicle_id:
        return jsonify({'message': 'Parameter vehicle_id is required'}), 400

    # Retrieve record using modern SQLAlchemy syntax
    vehicle = db.session.get(VehicleDAO, vehicle_id)

    if vehicle is None:
        return jsonify({'message': 'Vehicle not found'}), 404

    try:
        db.session.delete(vehicle)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({'message': 'Database error occurred while deleting vehicle'}), 500

    return '', 204
