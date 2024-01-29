from flask import Blueprint, jsonify, request
from route_consumption_estimator.api.models import *
from route_consumption_estimator.api.security import api_required

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
    vehicle = Vehicle.query.filter_by(name=name).first()
    # Check if the vehicle exists
    if vehicle is None:
        # Return A 404 not found error
        return jsonify({'message': 'Vehicle not found'}), 404
    # Serialize the vehicle as JSON
    result = vehicle_schema.dump(vehicle)
    # Return the JSON response
    return jsonify(result)


# Create A route to create A new vehicle
@vehicles_bp.route('/vehicles', methods=['POST'])
@api_required
def create_vehicle():
    # Get the JSON data from the request
    data = request.get_json()
    # Validate the data
    if 'Name' not in data or 'MotorType' not in data or 'PMaxKw' not in data or 'ConsumptionkWh' not in data \
            or 'C' not in data:
        # Return A 400 bad request error
        return jsonify({'message': 'Missing data'}), 400
    # TODO add values if not defined
    # Create A new vehicle object
    vehicle = Vehicle(data.get('Name'), data.get('MotorType'), data.get('UnladenVehMass'), data.get('LoadVehMass'),
                      data.get('NumSeats'), data.get('Longitude'), data.get('Width'), data.get('Height'),
                      data.get('ResistanceFactor'), data.get('PMaxKw'), data.get('ConsumptionkWh'), data.get('Gearbox'),
                      data.get('A'), data.get('C'), data.get('Url'), data.get('ImageUrl'))
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
