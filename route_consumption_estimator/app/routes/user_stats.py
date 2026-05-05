from flask import Blueprint, jsonify, request

from route_consumption_estimator.domain import *
from route_consumption_estimator.app.security import api_required

# user_stats blueprint
user_stats_bp = Blueprint('user_stats', __name__)

user_stat_schema = UserStatsDAOSchema()
user_stats_schema = UserStatsDAOSchema(many=True)
user_routes_schema = UserRouteDAOSchema(many=True)


# Create an endpoint to get all user stats
@user_stats_bp.route('/user_stats', methods=['GET'])
@api_required
def get_user_stats():
    # Retrieve query params (user)
    user = request.args.get('user', '')
    if user:
        # Query the database for the user stats of a given user (included in a list to fit the output schema)
        user_stats = [UserStatsDAO.query.get(user)]
    else:
        # Query the database for all user stats
        user_stats = UserStatsDAO.query.all()
    # Serialize the user stats as JSON
    result = user_stats_schema.dump(user_stats)
    # Return the JSON response
    return jsonify(result)


# Create an endpoint to create a new user stats
@user_stats_bp.route('/user_stats', methods=['POST'])
@api_required
def create_user_stats():
    # Get the JSON data from the request
    data = request.get_json()
    # Validate the data
    if 'UserID' not in data or 'ConsumptionSaving' not in data or 'EcoTime' not in data or 'EcoDistance' not in data \
            or 'EcoRoutesNum' not in data or 'DriveRating' not in data:
        # Return A 400 bad request error
        return jsonify({'message': 'Missing data'}), 400
    # Create A new user stat object
    user_stat = UserStatsDAO(UserID=data['UserID'], ConsumptionSaving=data['ConsumptionSaving'],
                             EcoTime=data['EcoTime'],
                             EcoDistance=data['EcoDistance'], EcoRoutesNum=data['EcoRoutesNum'],
                             DriveRating=data['DriveRating'])
    # Add the user stat to the database
    db.session.add(user_stat)
    db.session.commit()
    # Serialize the user stat as JSON
    result = user_stat_schema.dump(user_stat)
    # Return the JSON response with A 201 created status
    return jsonify(result), 201


# Create and endpoint to update the user stats by user ID
@user_stats_bp.route('/user_stats', methods=['PUT'])
@api_required
def update_user_stats():
    # Get the JSON data from the request
    data = request.get_json()
    user_id = data.get('UserID')
    # Check if the parameter not set
    if not user_id:
        # Return A 404 not found error
        return jsonify({'message': 'UserID is required'}), 404

    # Query the database for the user stat with the given user ID
    user_stat = UserStatsDAO.query.get(user_id)
    # Check if the user stat exists
    if user_stat is None:
        # Return A 404 not found error
        return jsonify({'message': 'User stat not found'}), 404

    # Update the user stats attributes
    user_stat.ConsumptionSaving = data.get('ConsumptionSaving', user_stat.ConsumptionSaving)
    user_stat.EcoTime = data.get('EcoTime', user_stat.EcoTime)
    user_stat.EcoDistance = data.get('EcoDistance', user_stat.EcoDistance)
    user_stat.EcoRoutesNum = data.get('EcoRoutesNum', user_stat.EcoRoutesNum)
    user_stat.DriveRating = data.get('DriveRating', user_stat.DriveRating)
    # Commit the changes to the database
    db.session.commit()
    # Serialize the user stat as JSON
    result = user_stats_schema.dump(user_stat)
    # Return the JSON response
    return jsonify(result)


# Create an endpoint to delete a user stat by user ID
@user_stats_bp.route('/user_stats', methods=['DELETE'])
@api_required
def delete_user_stats():
    # Retrieve query params (user)
    user = request.args.get('user', '')
    # Check if the parameter not set
    if not user:
        # Return A 404 not found error
        return jsonify({'message': 'user is required'}), 404

    # Query the database for the user stat with the given user ID
    user_stat = UserStatsDAO.query.get(user)
    # Check if the user stat exists
    if user_stat is None:
        # Return A 404 not found error
        return jsonify({'message': 'User stats not found'}), 404
    # Delete the user stat from the database
    db.session.delete(user_stat)
    db.session.commit()
    # Return A 204 no content status
    return '', 204
