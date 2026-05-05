from flask import Blueprint, jsonify, request, current_app
from route_consumption_estimator.domain import *
from route_consumption_estimator.app.security import api_required

# vehicles blueprint
vehicles_bp = Blueprint('vehicles', __name__)

# Create the Vehicle schema objects
vehicle_schema = VehicleDAOSchema()
vehicles_schema = VehicleDAOSchema(many=True)


# Create an endpoint to get all or filtered by name vehicles
@vehicles_bp.route('/vehicles', methods=['GET'])
@api_required
def get_vehicles():
    # Retrieve query params (q, id)
    query = request.args.get('q', '')
    vehicle_id = request.args.get('vehicle_id', '')
    if query:
        # Query the database for the vehicles that match the input query on name
        vehicles = VehicleDAO.query.filter(VehicleDAO.Name.like('%' + query + '%'))
    elif vehicle_id:
        # Query the database for the vehicle with the given ID (included in a list to fit the output schema)
        vehicles = [VehicleDAO.query.get(vehicle_id)]
    else:
        # Query the database for all vehicles
        vehicles = VehicleDAO.query.all()
    # Serialize the vehicles as JSON
    result = vehicles_schema.dump(vehicles)
    # Return the JSON response
    return jsonify(result)


# Create an endpoint to create a vehicle
@vehicles_bp.route('/vehicles', methods=['POST'])
@api_required
def create_vehicle():
    current_app_config = current_app.config["APP_CONFIG"].system

    # Get the JSON data from the request
    data = request.get_json()
    # Validate the data
    if 'Name' not in data or 'MotorType' not in data or 'UnladenVehMass' not in data or 'PMaxKw' not in data:
        # Return A 400 bad request error
        return jsonify({'message': 'Missing data'}), 400
    # Calculate A: it would be added the load mass, but as it is on each execution, watch out
    # A = ResistanceFactor * (UnladenVehMass + AdditionalMass) * 9,81
    A = data.get('A',
                 data.get('ResistanceFactor', current_app_config.vehicle_default_rf) * (
                         data.get('UnladenVehMass') + current_app_config.default_passenger_additional_mass) * GRAVITY)
    # Get B or at least by default value
    B = data.get('B', current_app_config.vehicle_default_b)
    # Calculate C
    # FrontalArea = 0.85 * Width (m) * Height (m)
    # Parse Width and Height to meters
    FrontalArea = 0.85 * data.get('Width', 0) / 1000 * data.get('Height', 0) / 1000
    # C = 0.5 * 1.225 * FrontalArea * Cx * (1 / 3.6)^2

    C = data.get('C',
                 0.5 * 1.225 * data.get('FrontalArea', FrontalArea) *
                 data.get('Cx', current_app_config.vehicle_default_cx) *
                 (1 / 3.6) ** 2)

    LitersConversion = 0
    if data.get('MotorType') == "Gasoline":
        LitersConversion = current_app_config.vehicle_default_gasoline_conversion
    elif data.get('MotorType') == "Diesel":
        LitersConversion = current_app_config.vehicle_default_diesel_conversion

    # Create A new vehicle object
    vehicle = VehicleDAO(Name=data.get('Name'),
                         MotorType=data.get('MotorType'),
                         UnladenVehMass=data.get('UnladenVehMass'),
                         PMaxKw=data.get('PMaxKw'),
                         LitersConversion=data.get('LitersConversion', LitersConversion),
                         ResistanceFactor=data.get('ResistanceFactor', current_app_config.vehicle_default_rf),
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
    vehicle = VehicleDAO.query.get(vehicle_id)
    # Check if the vehicle exists
    if vehicle is None:
        # Return A 404 not found error
        return jsonify({'message': 'Vehicle not found'}), 404
    # Delete the vehicle from the database
    db.session.delete(vehicle)
    db.session.commit()
    # Return A 204 no content status
    return '', 204
