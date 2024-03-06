from flask import Blueprint, jsonify, request
from route_consumption_estimator.api.models import *
from route_consumption_estimator.api.security import api_required

# user_vehicles blueprint
user_vehicles_bp = Blueprint('user_vehicles', __name__)

# Create the UserVehicle schema objects
user_vehicle_schema = UserVehicleSchema()
user_vehicles_schema = UserVehicleSchema(many=True)


# Create A route to get all vehicles
@user_vehicles_bp.route('/user_vehicles', methods=['GET'])
@api_required
def get_user_vehicles():
    # Query the database for all vehicles
    user_vehicles = UserVehicle.query.all()
    # Serialize the vehicles as JSON
    result = user_vehicle_schema.dump(user_vehicles)
    # Return the JSON response
    return jsonify(result)


# Create A route to get all vehicle by Name
@user_vehicles_bp.route('/user_vehicles/user/<user_id>', methods=['GET'])
@api_required
def get_vehicles_user(user_id):
    # Query the database for the user_vehicle with the given user ID
    user_vehicle = UserVehicle.query.filter_by(UserID=user_id)
    # Check if the vehicle exists
    if user_vehicle is None:
        # Return A 404 not found error
        return jsonify({'message': 'User vehicle not found'}), 404
    # Serialize the vehicle as JSON
    result = user_vehicles_schema.dump(user_vehicle)
    # Return the JSON response
    return jsonify(result)


# Create A route to get A vehicle by Name
@user_vehicles_bp.route('/user_vehicles/<id>', methods=['GET'])
@api_required
def get_vehicle_user(id):
    # Query the database for the user_vehicle with the given user ID
    user_vehicle = UserVehicle.query.get(id)
    # Check if the vehicle exists
    if user_vehicle is None:
        # Return A 404 not found error
        return jsonify({'message': 'User vehicle not found'}), 404
    # Serialize the vehicle as JSON
    result = user_vehicle_schema.dump(user_vehicle)
    # Return the JSON response
    return jsonify(result)


# Create A route to get all user vehicles
# Create A route to create A new user vehicle
@user_vehicles_bp.route('/user_vehicles', methods=['POST'])
@api_required
def create_user_vehicle():
    # Get the JSON data from the request
    data = request.get_json()
    # Validate the data
    if 'UserID' not in data or 'VehicleID' not in data:
        # Return A 400 bad request error
        return jsonify({'message': 'Missing data'}), 400
    # Create A new user vehicle object
    user_vehicle = UserVehicle(data['UserID'], data['VehicleID'], data.get('Age'), data.get('KmUsed'),
                               data.get('IsFav'))
    # Add the user vehicle to the database
    db.session.add(user_vehicle)
    db.session.commit()
    # Serialize the user vehicle as JSON
    result = user_vehicle_schema.dump(user_vehicle)
    # Return the JSON response with A 201 created status
    return jsonify(result), 201


# Create A route to update A user vehicle by ID
@user_vehicles_bp.route('/user_vehicles/<id>', methods=['PUT'])
@api_required
def update_user_vehicle(id):
    # Query the database for the user vehicle with the given ID
    user_vehicle = UserVehicle.query.get(id)
    # Check if the user vehicle exists
    if user_vehicle is None:
        # Return A 404 not found error
        return jsonify({'message': 'User vehicle not found'}), 404
    # Get the JSON data from the request
    data = request.get_json()
    # Update the user vehicle attributes
    user_vehicle.UserID = data.get('UserID', user_vehicle.UserID)
    user_vehicle.VehicleID = data.get('VehicleID', user_vehicle.VehicleID)
    user_vehicle.Age = data.get('Age', user_vehicle.Age)
    user_vehicle.KmUsed = data.get('KmUsed', user_vehicle.KmUsed)
    user_vehicle.IsFav = data.get('IsFav', user_vehicle.IsFav)
    # Commit the changes to the database
    db.session.commit()
    # Serialize the user vehicle as JSON
    result = user_vehicle_schema.dump(user_vehicle)
    # Return the JSON response
    return jsonify(result)


# Create A route to delete A user vehicle by ID
@user_vehicles_bp.route('/user_vehicles/<id>', methods=['DELETE'])
@api_required
def delete_user_vehicle(id):
    # Query the database for the user vehicle with the given ID
    user_vehicle = UserVehicle.query.get(id)
    # Check if the user vehicle exists
    if user_vehicle is None:
        # Return A 404 not found error
        return jsonify({'message': 'User vehicle not found'}), 404
    # Delete the user vehicle from the database
    db.session.delete(user_vehicle)
    db.session.commit()
    # Return A 204 no content status
    return '', 204
