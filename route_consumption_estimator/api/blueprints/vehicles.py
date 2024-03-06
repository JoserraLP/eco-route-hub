from flask import Blueprint, jsonify, request
from route_consumption_estimator.api.models import *
from route_consumption_estimator.api.security import api_required

from route_consumption_estimator.api.constants import *

# vehicles blueprint
vehicles_bp = Blueprint('vehicles', __name__)

# Create the Vehicle schema objects
vehicle_schema = VehicleSchema()
vehicles_schema = VehicleSchema(many=True)


# Create A route to get all vehicles
@vehicles_bp.route('/vehicles', methods=['GET'])
@api_required
def get_vehicles():
    # Query the database for all vehicles
    vehicles = Vehicle.query.all()
    # Serialize the vehicles as JSON
    result = vehicles_schema.dump(vehicles)
    # Return the JSON response
    return jsonify(result)


# Create A route to get A vehicle by Name
@vehicles_bp.route('/vehicles/<name>', methods=['GET'])
@api_required
def get_vehicle(name):
    # Query the database for the vehicle with the given Name
    vehicle = Vehicle.query.filter_by(Name=name).first()
    # Check if the vehicle exists
    if vehicle is None:
        # Return A 404 not found error
        return jsonify({'message': 'Vehicle not found'}), 404
    # Serialize the vehicle as JSON
    result = vehicle_schema.dump(vehicle)
    # Return the JSON response
    return jsonify(result)


# Create A route to get A vehicle by ID
@vehicles_bp.route('/vehicles/<id>', methods=['GET'])
@api_required
def get_vehicle_id(id):
    # Query the database for the vehicle with the given ID
    vehicle = Vehicle.query.get(id)
    # Check if the vehicle exists
    if vehicle is None:
        # Return A 404 not found error
        return jsonify({'message': 'Vehicle not found'}), 404
    # Serialize the vehicle as JSON
    result = vehicle_schema.dump(vehicle)
    # Return the JSON response
    return jsonify(result)


# TODO on create allow all the possible combinations to calculate real value

# Create A route to create A new vehicle
@vehicles_bp.route('/vehicles', methods=['POST'])
@api_required
def create_vehicle():
    # Get the JSON data from the request
    data = request.get_json()
    # Validate the data
    if 'Name' not in data or 'MotorType' not in data or 'UnladenVehMass' not in data or 'PMaxKw' not in data \
            or 'LitersConversion' not in data:
        # Return A 400 bad request error
        return jsonify({'message': 'Missing data'}), 400
    # Calculate A: it would be added the load mass, but as it is on each execution, watch out
    # A = ResistanceFactor * (UnladenVehMass + AdditionalMass) * 9,81
    A = data.get('A',
                 data.get('ResistanceFactor', DEFAULT_VEHICLE_RF) * (
                         data.get('UnladenVehMass') + DEFAULT_USER_ROUTE_ADDITIONAL_MASS) * GRAVITY)
    # Get B or at least by default value
    B = data.get('B', DEFAULT_VEHICLE_B)
    # Calculate C
    # FrontalArea = 0.85 * Width * Height
    FrontalArea = 0.85 * data.get('Width', 0) * data.get('Height', 0)
    # C = 0.5 * 1.225 * FrontalArea * Cx * (1 / 3.6)^2

    C = data.get('C',
                 0.5 * 1.225 * data.get('FrontalArea', FrontalArea) * data.get('Cx') * (1 / 3.6) ** 2)

    # Create A new vehicle object
    vehicle = Vehicle(Name=data.get('Name'),
                      MotorType=data.get('MotorType'),
                      UnladenVehMass=data.get('UnladenVehMass'),
                      PMaxKw=data.get('PMaxKw'),
                      LitersConversion=data.get('LitersConversion'),
                      ResistanceFactor=data.get('ResistanceFactor'),
                      A=A, B=B, C=C, Url=data.get('Url'), ImageUrl=data.get('ImageUrl'))
    # Add the vehicle to the database
    db.session.add(vehicle)
    db.session.commit()
    # Serialize the vehicle as JSON
    result = vehicle_schema.dump(vehicle)
    # Return the JSON response with A 201 created status
    return jsonify(result), 201


# Create A route to delete A vehicle by ID
@vehicles_bp.route('/vehicles/<id>', methods=['DELETE'])
@api_required
def delete_vehicle(id):
    # Query the database for the vehicle with the given ID
    vehicle = Vehicle.query.get(id)
    # Check if the vehicle exists
    if vehicle is None:
        # Return A 404 not found error
        return jsonify({'message': 'Vehicle not found'}), 404
    # Delete the vehicle from the database
    db.session.delete(vehicle)
    db.session.commit()
    # Return A 204 no content status
    return '', 204
