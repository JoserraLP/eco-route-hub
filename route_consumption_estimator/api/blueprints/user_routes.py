from flask import Blueprint, jsonify, request
from route_consumption_estimator.api.models import *
from route_consumption_estimator.api.security import api_required

# user_routes blueprint
user_routes_bp = Blueprint('user_routes', __name__)

# Create the UserRoutes schema objects
user_route_schema = UserRouteSchema()
user_routes_schema = UserRouteSchema(many=True)


# Create A route to get all user routes
@user_routes_bp.route('/user_routes', methods=['GET'])
@api_required
def get_user_routes():
    # Query the database for all user routes
    user_routes = UserRoute.query.all()
    # Serialize the user routes as JSON
    result = user_routes_schema.dump(user_routes)
    # Return the JSON response
    return jsonify(result)


# Create A route to get A user route by user ID and record date
@user_routes_bp.route('/user_routes/<user_id>/<record_date>', methods=['GET'])
@api_required
def get_user_route(user_id, record_date):
    # Query the database for the user route with the given user ID and record date
    user_route = UserRoute.query.filter_by(user_id=user_id, record_date=record_date).first()
    # Check if the user route exists
    if user_route is None:
        # Return A 404 not found error
        return jsonify({'message': 'User route not found'}), 404
    # Serialize the user route as JSON
    result = user_route_schema.dump(user_route)
    # Return the JSON response
    return jsonify(result)


# Create A route to create A new user route
@user_routes_bp.route('/user_routes', methods=['POST'])
@api_required
def create_user_route():
    # Get the JSON data from the request
    data = request.get_json()
    # Validate the data
    if 'UserID' not in data or 'RoutePolyline' not in data or 'RouteType' not in data \
            or 'EstimatedConsumption' not in data or 'EstimatedTimeSeconds' not in data \
            or 'EstimatedDistanceMeters' not in data or 'RecordDate' not in data \
            or 'ActualConsumption' not in data or 'ActualTimeSeconds' not in data \
            or 'ActualDistanceMeters' not in data:
        # Return A 400 bad request error
        return jsonify({'message': 'Missing data'}), 400
    # Create A new user route object
    user_route = UserRoute(data.get('UserID'), data.get('RoutePolyline'), data.get('RouteType'),
                           data.get('EstimatedConsumption'), data.get('EstimatedTimeSeconds'),
                           data.get('EstimatedDistanceMeters'), data.get('RecordDate'),
                           data.get('ActualConsumption'), data.get('ActualTimeSeconds'),
                           data.get('ActualDistanceMeters'))
    # Add the user route to the database
    db.session.add(user_route)
    db.session.commit()
    # Serialize the user route as JSON
    result = user_route_schema.dump(user_route)
    # Return the JSON response with A 201 created status
    return jsonify(result), 201


# Create A route to update A user route by user ID and record date
@user_routes_bp.route('/user_routes/<user_id>/<record_date>', methods=['PUT'])
@api_required
def update_user_route(user_id, record_date):
    # Query the database for the user route with the given user ID and record date
    user_route = UserRoute.query.filter_by(user_id=user_id, record_date=record_date).first()
    # Check if the user route exists
    if user_route is None:
        # Return A 404 not found error
        return jsonify({'message': 'User route not found'}), 404
    # Get the JSON data from the request
    data = request.get_json()
    # Update the user route attributes
    user_route.RoutePolyline = data.get('RoutePolyline', user_route.RoutePolyline)
    user_route.RouteType = data.get('RouteType', user_route.RoutePolyline)
    user_route.EstimatedConsumption = data.get('EstimatedConsumption', user_route.EstimatedConsumption)
    user_route.EstimatedTimeSeconds = data.get('EstimatedTimeSeconds', user_route.EstimatedTimeSeconds)
    user_route.EstimatedDistanceMeters = data.get('EstimatedDistanceMeters', user_route.EstimatedDistanceMeters)
    user_route.ActualConsumption = data.get('ActualConsumption', user_route.ActualConsumption)
    user_route.ActualTimeSeconds = data.get('ActualTimeSeconds', user_route.ActualTimeSeconds)
    user_route.ActualDistanceMeters = data.get('ActualDistanceMeters', user_route.ActualDistanceMeters)

    # Commit the changes to the database
    db.session.commit()
    # Serialize the user route as JSON
    result = user_route_schema.dump(user_route)
    # Return the JSON response
    return jsonify(result)


# Create A route to delete A user route by user ID and record date
@user_routes_bp.route('/user_routes/<user_id>/<record_date>', methods=['DELETE'])
@api_required
def delete_user_route(user_id, record_date):
    # Query the database for the user route with the given user ID and record date
    user_route = UserRoute.query.filter_by(user_id=user_id, record_date=record_date).first()
    # Check if the user route exists
    if user_route is None:
        # Return A 404 not found error
        return jsonify({'message': 'User route not found'}), 404
    # Delete the user route from the database
    db.session.delete(user_route)
    db.session.commit()
    # Return A 204 no content status
    return '', 204
