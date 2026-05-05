from flask import Blueprint, jsonify, request
from route_consumption_estimator.domain import *
from route_consumption_estimator.app.security import api_required

# feature_review blueprint
feature_review_bp = Blueprint('feature_review', __name__)

# Create the FeatureReview schema objects
feature_review_schema = FeatureReviewDAOSchema()
feature_reviews_schema = FeatureReviewDAOSchema(many=True)


# Create an endpoint to get all or filtered feature_reviews
@feature_review_bp.route('/feature_review', methods=['GET'])
@api_required
def get_feature_reviews():
    # Retrieve query params (app_review_id, feature_review_id)
    app_review_id = request.args.get('app_review_id', '')
    feature_review_id = request.args.get('feature_review_id', '')
    if app_review_id:
        feature_reviews = FeatureReviewDAO.query.filter_by(AppReviewID=app_review_id)
    elif feature_review_id:
        # Query the database for the feature_review with the given user ID
        feature_reviews = [FeatureReviewDAO.query.get(feature_review_id)]
    else:
        # Query the database for all feature reviews
        feature_reviews = FeatureReviewDAO.query.all()

    # Serialize the vehicles as JSON
    result = feature_reviews_schema.dump(feature_reviews)
    # Return the JSON response
    return jsonify(result)


# Create an endpoint to create a new feature review
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
    feature_review = FeatureReviewDAO(AppReviewID=data['AppReviewID'], Topic=data.get('Topic'), Score=data.get('Score'),
                                      Comments=data.get('Comments'))
    # Add the app review to the database
    db.session.add(feature_review)
    db.session.commit()
    # Serialize the app review as JSON
    result = feature_review_schema.dump(feature_review)
    # Return the JSON response with A 201 created status
    return jsonify(result), 201


# Create an endpoint to delete a feature review by ID
@feature_review_bp.route('/feature_review', methods=['DELETE'])
@api_required
def delete_feature_review():
    # Retrieve query params (user, app_review_id)
    feature_review_id = request.args.get('feature_review_id', '')
    # Check if the parameter not set
    if not feature_review_id:
        # Return A 404 not found error
        return jsonify({'message': 'feature_review_id is required'}), 404

    # Query the database for the feature review with the given ID
    feature_review = FeatureReviewDAO.query.get(feature_review_id)
    # Check if the app review exists
    if feature_review is None:
        # Return A 404 not found error
        return jsonify({'message': 'Feature review not found'}), 404
    # Delete the app review from the database
    db.session.delete(feature_review)
    db.session.commit()
    # Return A 204 no content status
    return '', 204
