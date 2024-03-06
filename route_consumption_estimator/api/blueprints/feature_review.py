from flask import Blueprint, jsonify, request
from route_consumption_estimator.api.models import *
from route_consumption_estimator.api.security import api_required

# feature_review blueprint
feature_review_bp = Blueprint('feature_review', __name__)

# Create the FeatureReview schema objects
feature_review_schema = FeatureReviewSchema()
feature_reviews_schema = FeatureReviewSchema(many=True)


# Create A route to get all vehicles
@feature_review_bp.route('/feature_review', methods=['GET'])
@api_required
def get_feature_reviews():
    # Query the database for all vehicles
    feature_review = FeatureReview.query.all()
    # Serialize the vehicles as JSON
    result = feature_review_schema.dump(feature_review)
    # Return the JSON response
    return jsonify(result)


# Create A route to get all review by app review ID
@feature_review_bp.route('/feature_review/app_review_id/<app_review_id>', methods=['GET'])
@api_required
def get_app_feature_reviews(app_review_id):
    # Query the database for the feature_review with the given app review ID
    feature_review = FeatureReview.query.filter_by(AppReviewID=app_review_id)
    # Check if the vehicle exists
    if feature_review is None:
        # Return A 404 not found error
        return jsonify({'message': 'Feature review not found'}), 404
    # Serialize the vehicle as JSON
    result = feature_reviews_schema.dump(feature_review)
    # Return the JSON response
    return jsonify(result)


# Create A route to get an app review by ID
@feature_review_bp.route('/feature_review/<id>', methods=['GET'])
@api_required
def get_feature_review(id):
    # Query the database for the feature_review with the given user ID
    feature_review = FeatureReview.query.get(id)
    # Check if the vehicle exists
    if feature_review is None:
        # Return A 404 not found error
        return jsonify({'message': 'Feature review not found'}), 404
    # Serialize the vehicle as JSON
    result = feature_review_schema.dump(feature_review)
    # Return the JSON response
    return jsonify(result)


# Create A route to get all user vehicles
# Create A route to create A new app review
@feature_review_bp.route('/feature_review', methods=['POST'])
@api_required
def create_feature_review():
    # Get the JSON data from the request
    data = request.get_json()
    # Validate the data
    if 'AppReviewID' not in data:
        # Return A 400 bad request error
        return jsonify({'message': 'Missing data'}), 400
    # Create A new app review object
    feature_review = FeatureReview(data['AppReviewID'], data.get('Topic'), data.get('Score'),
                                   data.get('Comments'))
    # Add the app review to the database
    db.session.add(feature_review)
    db.session.commit()
    # Serialize the app review as JSON
    result = feature_review_schema.dump(feature_review)
    # Return the JSON response with A 201 created status
    return jsonify(result), 201


# Create A route to update an app review by ID
@feature_review_bp.route('/feature_review/<id>', methods=['PUT'])
@api_required
def update_feature_review(id):
    # Query the database for the app review with the given ID
    feature_review = FeatureReview.query.get(id)
    # Check if the app review exists
    if feature_review is None:
        # Return A 404 not found error
        return jsonify({'message': 'Feature review not found'}), 404
    # Get the JSON data from the request
    data = request.get_json()
    # Update the app review attributes
    feature_review.AppReviewID = data.get('AppReviewID', feature_review.AppReviewID)
    feature_review.Topic = data.get('Topic', feature_review.Topic)
    feature_review.Score = data.get('Score', feature_review.Score)
    feature_review.Comments = data.get('Comments', feature_review.Comments)

    # Commit the changes to the database
    db.session.commit()
    # Serialize the app review as JSON
    result = feature_review_schema.dump(feature_review)
    # Return the JSON response
    return jsonify(result)


# Create A route to delete an app review by ID
@feature_review_bp.route('/feature_review/<id>', methods=['DELETE'])
@api_required
def delete_feature_review(id):
    # Query the database for the app review with the given ID
    feature_review = FeatureReview.query.get(id)
    # Check if the app review exists
    if feature_review is None:
        # Return A 404 not found error
        return jsonify({'message': 'Feature review not found'}), 404
    # Delete the app review from the database
    db.session.delete(feature_review)
    db.session.commit()
    # Return A 204 no content status
    return '', 204
