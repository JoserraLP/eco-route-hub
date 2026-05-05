import numpy as np
from flask import Blueprint, jsonify, request, current_app

from route_consumption_estimator.app.security import api_required
from route_consumption_estimator.domain import *

# user_routes blueprint
user_routes_bp = Blueprint('user_routes', __name__)

# Create the UserRoutes schema objects
user_route_schema = UserRouteDAOSchema()
user_routes_schema = UserRouteDAOSchema(many=True)


# Create and endpoint to get all or a given user user_routes
@user_routes_bp.route('/user_routes', methods=['GET'])
@api_required
def get_user_routes():
    # Retrieve query params (user)
    user = request.args.get('user', '')
    if user:
        # Query the database for the user_routes with the given user
        user_routes = UserRouteDAO.query.filter_by(UserID=user).order_by(UserRouteDAO.RecordDate.desc()).limit(5)
    else:
        # Query the database for all user routes
        user_routes = UserRouteDAO.query.all()
    # Serialize the user routes as JSON
    result = user_routes_schema.dump(user_routes)
    # Return the JSON response
    return jsonify(result)


# Create an endpoint to create a new user route
@user_routes_bp.route('/user_routes', methods=['POST'])
@api_required
def create_user_route():
    current_app_config = current_app.config["APP_CONFIG"].system

    # Get the JSON data from the request
    data = request.get_json()
    # Validate the data
    keys = set(data.keys())
    strings_to_check = {
        "UserID", "UserVehicleID", "AdditionalMass", "SourceCoords",
        "DestinationCoords", "SelectedRoutePolyline",
        "SelectedRouteType", "SelectedRouteConsumption", "SelectedRouteTime",
        "SelectedRouteDistance", "PerformedRoutePolyline", "PerformedRouteConsumption",
        "PerformedRouteTime", "PerformedRouteDistance", "PerformedRouteEstimatedConsumption",
        "PerformedRouteEstimatedTime", "PerformedRouteEstimatedDistance", "NumStopsKm", "SpeedVariationNum",
        "DrivingAggressiveness"
    }
    if not strings_to_check.issubset(keys):
        # Return A 400 bad request error
        return jsonify({'message': 'Missing data'}), 400

    # Get current datetime
    now = datetime.now()

    # Create a new user route object with default values if not defined
    user_route = UserRouteDAO(UserID=data.get('UserID'),
                              UserVehicleID=data.get('UserVehicleID'),
                              AdditionalMass=data.get('AdditionalMass',
                                                      current_app_config.default_passenger_additional_mass),
                              SourceCoords=data.get('SourceCoords'),
                              DestinationCoords=data.get('DestinationCoords'),
                              SelectedRoutePolyline=data.get('SelectedRoutePolyline'),
                              SelectedRouteType=data.get('SelectedRouteType'),
                              SelectedRouteConsumption=data.get('SelectedRouteConsumption'),
                              SelectedRouteTime=data.get('SelectedRouteTime'),
                              SelectedRouteDistance=data.get('SelectedRouteDistance'),
                              PerformedRoutePolyline=data.get('PerformedRoutePolyline'),
                              PerformedRouteConsumption=data.get('PerformedRouteConsumption'),
                              PerformedRouteTime=data.get('PerformedRouteTime'),
                              PerformedRouteDistance=data.get('PerformedRouteDistance'),
                              PerformedRouteEstimatedConsumption=data.get('PerformedRouteEstimatedConsumption'),
                              PerformedRouteEstimatedTime=data.get('PerformedRouteEstimatedTime'),
                              PerformedRouteEstimatedDistance=data.get('PerformedRouteEstimatedDistance'),
                              NumStopsKm=data.get('NumStopsKm'),
                              SpeedVariationNum=data.get('SpeedVariationNum'),
                              DrivingAggressiveness=data.get('DrivingAggressiveness'),
                              RecordDate=now.strftime('%Y-%m-%d %H:%M:%S')
                              )

    # Add the user route to the database
    db.session.add(user_route)
    db.session.commit()

    recalculate_user_stats(data.get('UserID'))

    # Serialize the user route as JSON
    result = user_route_schema.dump(user_route)
    # Return the JSON response with A 201 created status
    return jsonify(result), 201


def recalculate_user_stats(user_id):
    """
    Method to recalculate the user stats based on all the user_routes

    :param user_id: user identifier
    :return:
    """

    # Query all the user routes
    user_routes = UserRouteDAO.query.filter_by(UserID=user_id)

    user_routes = user_routes_schema.dump(user_routes)

    # Define variable to store the values
    total_estimated_consumption = 0.0
    total_real_consumption = 0.0
    eco_time = 0.0
    total_time = 0.0
    eco_distance = 0.0
    total_distance = 0.0
    eco_routes_num = 0
    drive_rating = []

    for user_route in user_routes:
        # Difference of performed routes consumptions
        total_estimated_consumption += float(user_route['PerformedRouteEstimatedConsumption'])
        total_real_consumption += float(user_route['PerformedRouteConsumption'])
        total_time += int(user_route['PerformedRouteTime'])
        total_distance += int(user_route['PerformedRouteDistance'])
        # Only count the selected route type if ECO and route is not selected
        if user_route['SelectedRouteType'] == 'ECO' and user_route['SelectedRoutePolyline'] != 'null':
            eco_time += int(user_route['PerformedRouteTime'])
            eco_distance += int(user_route['PerformedRouteDistance'])
            eco_routes_num += 1

        # average of all the three metrics
        # int(user_route['NumStopsKm'])
        drive_rating.append(np.mean([int(user_route['SpeedVariationNum']),
                                     int(user_route['DrivingAggressiveness'])]))

    # Query the database for the user stat with the given user ID
    user_stats = UserStatsDAO.query.get(user_id)

    # Update the user stats attributes
    user_stats.ConsumptionSaving = 100 * (total_estimated_consumption - total_real_consumption) / \
                                   max([total_estimated_consumption, total_real_consumption])
    user_stats.EcoTime = 100 * eco_time / total_time
    user_stats.EcoDistance = 100 * eco_distance / total_distance
    user_stats.EcoRoutesNum = 100 * eco_routes_num / len(drive_rating)
    user_stats.DriveRating = np.mean(drive_rating)

    # Commit the changes to the database
    db.session.commit()


# Create an endpoint to remove a user route by id
@user_routes_bp.route('/user_routes', methods=['DELETE'])
@api_required
def delete_user_route():
    user_route_id = request.args.get('user_route_id', '')
    # Check if the parameter not set
    if not user_route_id:
        # Return A 404 not found error
        return jsonify({'message': 'user_route_id is required'}), 404
    # Query the database for the user route with the given user route ID
    user_route = UserRouteDAO.query.get(user_route_id)
    # Check if the user route exists
    if user_route is None:
        # Return A 404 not found error
        return jsonify({'message': 'User route not found'}), 404
    # Delete the user route from the database
    db.session.delete(user_route)
    db.session.commit()
    # Return A 204 no content status
    return '', 204
