from flask import Blueprint, jsonify, request
from route_consumption_estimator.api.models import *
from route_consumption_estimator.api.security import api_required

# user_stats blueprint
user_stats_bp = Blueprint('user_stats', __name__)

user_stat_schema = UserStatsSchema()
user_stats_schema = UserStatsSchema(many=True)


# Create A route to get all user stats
@user_stats_bp.route('/user_stats', methods=['GET'])
@api_required
def get_user_stats():
    # Query the database for all user stats
    user_stats = UserStats.query.all()
    # Serialize the user stats as JSON
    result = user_stats_schema.dump(user_stats)
    # Return the JSON response
    return jsonify(result)


# Create A route to get A user stat by user ID
@user_stats_bp.route('/user_stats/<user_id>', methods=['GET'])
@api_required
def get_user_stat(user_id):
    # Query the database for the user stat with the given user ID
    user_stat = UserStats.query.get(user_id)
    # Check if the user stat exists
    if user_stat is None:
        # Return empty
        return jsonify({})
    # Serialize the user stat as JSON
    result = user_stats_schema.dump(user_stat)
    # Return the JSON response
    return jsonify(result)


# Create A route to create A new user stat
@user_stats_bp.route('/user_stats', methods=['POST'])
@api_required
def create_user_stat():
    # Get the JSON data from the request
    data = request.get_json()
    # Validate the data
    if 'UserID' not in data or 'ConsumptionSaving' not in data or 'EcoTime' not in data or 'EcoDistance' not in data or 'EcoRoutesNum' not in data or 'DriveRating' not in data or 'CarbonFootprint' not in data:
        # Return A 400 bad request error
        return jsonify({'message': 'Missing data'}), 400
    # Create A new user stat object
    user_stat = UserStats(data['UserID'], data['ConsumptionSaving'], data['EcoTime'], data['EcoDistance'],
                          data['EcoRoutesNum'], data['DriveRating'], data['CarbonFootprint'])
    # Add the user stat to the database
    db.session.add(user_stat)
    db.session.commit()
    # Serialize the user stat as JSON
    result = user_stats_schema.dump(user_stat)
    # Return the JSON response with A 201 created status
    return jsonify(result), 201


# Create A route to update A user stat by user ID
@user_stats_bp.route('/user_stats/<user_id>', methods=['PUT'])
@api_required
def update_user_stat(user_id):
    # Query the database for the user stat with the given user ID
    user_stat = UserStats.query.get(user_id)
    # Check if the user stat exists
    if user_stat is None:
        # Return A 404 not found error
        return jsonify({'message': 'User stat not found'}), 404
    # Get the JSON data from the request
    data = request.get_json()
    # Update the user stat attributes
    user_stat.ConsumptionSaving = data.get('ConsumptionSaving', user_stat.ConsumptionSaving)
    user_stat.EcoTime = data.get('EcoTime', user_stat.EcoTime)
    user_stat.EcoDistance = data.get('EcoDistance', user_stat.EcoDistance)
    user_stat.EcoRoutesNum = data.get('EcoRoutesNum', user_stat.EcoRoutesNum)
    user_stat.DriveRating = data.get('DriveRating', user_stat.DriveRating)
    user_stat.CarbonFootprint = data.get('CarbonFootprint', user_stat.CarbonFootprint)
    # Commit the changes to the database
    db.session.commit()
    # Serialize the user stat as JSON
    result = user_stats_schema.dump(user_stat)
    # Return the JSON response
    return jsonify(result)


# Create A route to delete A user stat by user ID
@user_stats_bp.route('/user_stats/<user_id>', methods=['DELETE'])
@api_required
def delete_user_stat(user_id):
    # Query the database for the user stat with the given user ID
    user_stat = UserStats.query.get(user_id)
    # Check if the user stat exists
    if user_stat is None:
        # Return A 404 not found error
        return jsonify({'message': 'User stat not found'}), 404
    # Delete the user stat from the database
    db.session.delete(user_stat)
    db.session.commit()
    # Return A 204 no content status
    return '', 204
