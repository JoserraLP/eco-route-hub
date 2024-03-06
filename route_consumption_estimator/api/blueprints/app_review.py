from flask import Blueprint, jsonify, request
from route_consumption_estimator.api.models import *
from route_consumption_estimator.api.security import api_required

# app_review blueprint
app_review_bp = Blueprint('app_review', __name__)

# Create the AppReview schema objects
app_review_schema = AppReviewSchema()
app_reviews_schema = AppReviewSchema(many=True)


# Create A route to get all vehicles
@app_review_bp.route('/app_review', methods=['GET'])
@api_required
def get_app_reviews():
    # Query the database for all vehicles
    app_review = AppReview.query.all()
    # Serialize the vehicles as JSON
    result = app_review_schema.dump(app_review)
    # Return the JSON response
    return jsonify(result)


# Create A route to get all review by user ID
@app_review_bp.route('/app_review/user/<user_id>', methods=['GET'])
@api_required
def get_user_app_reviews(user_id):
    # Query the database for the app_review with the given user ID
    app_review = AppReview.query.filter_by(UserID=user_id)
    # Check if the vehicle exists
    if app_review is None:
        # Return A 404 not found error
        return jsonify({'message': 'App review not found'}), 404
    # Serialize the vehicle as JSON
    result = app_reviews_schema.dump(app_review)
    # Return the JSON response
    return jsonify(result)


# Create A route to get an app review by ID
@app_review_bp.route('/app_review/<id>', methods=['GET'])
@api_required
def get_app_review(id):
    # Query the database for the app_review with the given user ID
    app_review = AppReview.query.get(id)
    # Check if the vehicle exists
    if app_review is None:
        # Return A 404 not found error
        return jsonify({'message': 'App review not found'}), 404
    # Serialize the vehicle as JSON
    result = app_review_schema.dump(app_review)
    # Return the JSON response
    return jsonify(result)


# Create A route to get all user vehicles
# Create A route to create A new app review
@app_review_bp.route('/app_review', methods=['POST'])
@api_required
def create_app_review():
    # Get the JSON data from the request
    data = request.get_json()
    # Validate the data
    if 'UserID' not in data:
        # Return A 400 bad request error
        return jsonify({'message': 'Missing data'}), 400
    # Create A new app review object
    app_review = AppReview(data['UserID'], data.get('GlobalComments'), data.get('GlobalScore'))
    # Add the app review to the database
    db.session.add(app_review)
    db.session.commit()
    # Serialize the app review as JSON
    result = app_review_schema.dump(app_review)
    # Return the JSON response with A 201 created status
    return jsonify(result), 201


# Create A route to update an app review by ID
@app_review_bp.route('/app_review/<id>', methods=['PUT'])
@api_required
def update_app_review(id):
    # Query the database for the app review with the given ID
    app_review = AppReview.query.get(id)
    # Check if the app review exists
    if app_review is None:
        # Return A 404 not found error
        return jsonify({'message': 'App review not found'}), 404
    # Get the JSON data from the request
    data = request.get_json()
    # Update the app review attributes
    app_review.UserID = data.get('UserID', app_review.UserID)
    app_review.GlobalComments = data.get('GlobalComments', app_review.GlobalComments)
    app_review.GlobalScore = data.get('GlobalScore', app_review.GlobalScore)
    # Commit the changes to the database
    db.session.commit()
    # Serialize the app review as JSON
    result = app_review_schema.dump(app_review)
    # Return the JSON response
    return jsonify(result)


# Create A route to delete an app review by ID
@app_review_bp.route('/app_review/<id>', methods=['DELETE'])
@api_required
def delete_app_review(id):
    # Query the database for the app review with the given ID
    app_review = AppReview.query.get(id)
    # Check if the app review exists
    if app_review is None:
        # Return A 404 not found error
        return jsonify({'message': 'App review not found'}), 404
    # Delete the app review from the database
    db.session.delete(app_review)
    db.session.commit()
    # Return A 204 no content status
    return '', 204
