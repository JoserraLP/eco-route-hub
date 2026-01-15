from flask import Blueprint, jsonify, request
from route_consumption_estimator.api.models import *
from route_consumption_estimator.api.security import api_required

from route_consumption_estimator.api.constants import *

# vehicles blueprint
vehicles_bp = Blueprint('vehicles', __name__)

# Create the Vehicle schema objects
vehicle_schema = VehicleSchema()
vehicles_schema = VehicleSchema(many=True)


# Create an endpoint to get all or filtered by name vehicles
@vehicles_bp.route('/vehicles', methods=['GET'])
@api_required
def get_vehicles():
    # Retrieve query params (q, id)
    query = request.args.get('q', '')
    vehicle_id = request.args.get('vehicle_id', '')
    if query:
        # Query the database for the vehicles that match the input query on name
        vehicles = Vehicle.query.filter(Vehicle.Name.like('%' + query + '%'))
    elif vehicle_id:
        # Query the database for the vehicle with the given ID (included in a list to fit the output schema)
        vehicles = [Vehicle.query.get(vehicle_id)]
    else:
        # Query the database for all vehicles
        vehicles = Vehicle.query.all()
    # Serialize the vehicles as JSON
    result = vehicles_schema.dump(vehicles)
    # Return the JSON response
    return jsonify(result)


# Create an endpoint to create a vehicle
@vehicles_bp.route('/vehicles', methods=['POST'])
@api_required
def create_vehicle():
    # Get the JSON data from the request
    data = request.get_json()
    # Validate the data
    if 'Name' not in data or 'MotorType' not in data or 'UnladenVehMass' not in data or 'PMaxKw' not in data:
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
    # FrontalArea = 0.85 * Width (m) * Height (m)
    # Parse Width and Height to meters
    FrontalArea = 0.85 * data.get('Width', 0) / 1000 * data.get('Height', 0) / 1000
    # C = 0.5 * 1.225 * FrontalArea * Cx * (1 / 3.6)^2

    C = data.get('C',
                 0.5 * 1.225 * data.get('FrontalArea', FrontalArea) * data.get('Cx', DEFAULT_VEHICLE_CX) *
                 (1 / 3.6) ** 2)

    LitersConversion = 0
    if data.get('MotorType') == "Gasoline":
        LitersConversion = DEFAULT_GASOLINE_CONVERSION
    elif data.get('MotorType') == "Diesel":
        LitersConversion = DEFAULT_DIESEL_CONVERSION

    # Create A new vehicle object
    vehicle = Vehicle(Name=data.get('Name'),
                      MotorType=data.get('MotorType'),
                      UnladenVehMass=data.get('UnladenVehMass'),
                      PMaxKw=data.get('PMaxKw'),
                      LitersConversion=data.get('LitersConversion', LitersConversion),
                      ResistanceFactor=data.get('ResistanceFactor', DEFAULT_VEHICLE_RF),
                      A=A, B=B, C=C, Url=data.get('Url', ''), ImageUrl=data.get('ImageUrl', ''))
    # Add the vehicle to the database
    db.session.add(vehicle)
    db.session.commit()
    # Serialize the vehicle as JSON
    result = vehicle_schema.dump(vehicle)
    # Return the JSON response with a 201 created status
    return jsonify(result), 201


# Create A route to delete A vehicle by ID
@vehicles_bp.route('/vehicles', methods=['DELETE'])
@api_required
def delete_vehicle():
    vehicle_id = request.args.get('vehicle_id', '')
    # Check if the parameter not set
    if not vehicle_id:
        # Return A 404 not found error
        return jsonify({'message': 'vehicle_id is required'}), 404
    # Query the database for the vehicle with the given ID
    vehicle = Vehicle.query.get(vehicle_id)
    # Check if the vehicle exists
    if vehicle is None:
        # Return A 404 not found error
        return jsonify({'message': 'Vehicle not found'}), 404
    # Delete the vehicle from the database
    db.session.delete(vehicle)
    db.session.commit()
    # Return A 204 no content status
    return '', 204
