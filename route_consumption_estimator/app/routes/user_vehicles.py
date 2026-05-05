from flask import Blueprint, jsonify, request
from route_consumption_estimator.domain import *
from route_consumption_estimator.app.security import api_required

# user_vehicles blueprint
user_vehicles_bp = Blueprint('user_vehicles', __name__)

# Create the UserVehicle schema objects
user_vehicle_schema = UserVehicleDAOSchema()
user_vehicles_schema = UserVehicleDAOSchema(many=True)


# Create an endpoint to get all, specific user or specific user_vehicles
@user_vehicles_bp.route('/user_vehicles', methods=['GET'])
@api_required
def get_users_vehicles():
    # Retrieve query params (user, user_vehicle_id)
    user = request.args.get('user', '')
    user_vehicle_id = request.args.get('user_vehicle_id', '')
    if user:
        # Query the database for the user_vehicle with the given user ID
        user_vehicles = UserVehicleDAO.query.filter_by(UserID=user)
    elif user_vehicle_id:
        # Query the database for the user_vehicle with the given ID (included in a list to fit the output schema)
        user_vehicles = [UserVehicleDAO.query.get(id)]
    else:
        # Query the database for all vehicles
        user_vehicles = UserVehicleDAO.query.all()
    # Serialize the vehicles as JSON
    result = user_vehicles_schema.dump(user_vehicles)
    # Return the JSON response
    return jsonify(result)


# Create an endpoint to create a new user_vehicle
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
    user_vehicle = UserVehicleDAO(UserID=data['UserID'], VehicleID=data['VehicleID'], Age=data.get('Age'),
                                  KmUsed=data.get('KmUsed'), IsFav=data.get('IsFav'))
    # Add the user vehicle to the database
    db.session.add(user_vehicle)
    db.session.commit()
    # Serialize the user vehicle as JSON
    result = user_vehicle_schema.dump(user_vehicle)
    # Return the JSON response with A 201 created status
    return jsonify(result), 201


# Create and endpoint to update a user vehicle by user ID
@user_vehicles_bp.route('/user_vehicles', methods=['PUT'])
@api_required
def update_user_vehicle():
    # Get the JSON data from the request
    data = request.get_json()
    user_vehicle_id = data.get('ID')
    # Check if the parameter not set
    if not user_vehicle_id:
        # Return A 404 not found error
        return jsonify({'message': 'ID is required'}), 404
    # Query the database for the user vehicle with the given ID
    user_vehicle = UserVehicleDAO.query.get(user_vehicle_id)
    # Check if the user vehicle exists
    if user_vehicle is None:
        # Return A 404 not found error
        return jsonify({'message': 'UserVehicle not found'}), 404

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


# Create an endpoint to delete a user vehicle by user ID
@user_vehicles_bp.route('/user_vehicles', methods=['DELETE'])
@api_required
def delete_user_vehicle():
    user_vehicle_id = request.args.get('user_vehicle_id', '')
    # Check if the parameter not set
    if not user_vehicle_id:
        # Return A 404 not found error
        return jsonify({'message': 'user_vehicle_id is required'}), 404

    # Query the database for the user vehicle with the given ID
    user_vehicle = UserVehicleDAO.query.get(user_vehicle_id)
    # Check if the user vehicle exists
    if user_vehicle is None:
        # Return A 404 not found error
        return jsonify({'message': 'UserVehicle not found'}), 404
    # Delete the user vehicle from the database
    db.session.delete(user_vehicle)
    db.session.commit()
    # Return A 204 no content status
    return '', 204
