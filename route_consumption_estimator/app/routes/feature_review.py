"""
Feature review route handlers.

Provides RESTful API endpoints for managing feedback regarding specific application 
features, including listing/filtering reviews, creating new feature reviews, and 
deleting existing entries.
"""

from typing import Tuple, Union
from flask import Blueprint, Response, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from route_consumption_estimator import db
from route_consumption_estimator.app.security import api_required
from route_consumption_estimator.domain.dao_models import FeatureReviewDAOSchema, FeatureReviewDAO

# Blueprint definition for feature reviews
feature_review_bp = Blueprint('feature_review', __name__)

# Schema initializations for serialization and validation
feature_review_schema = FeatureReviewDAOSchema()
feature_reviews_schema = FeatureReviewDAOSchema(many=True)


@feature_review_bp.route('/feature_review', methods=['GET'])
@api_required
def get_feature_reviews() -> Tuple[Response, int]:
    """
    Retrieve feature reviews based on query filters.

    Supports fetching all feature reviews, filtering by an associated application 
    review identifier (AppReviewID), or querying a single feature review by its ID.

    Query Parameters:
        app_review_id (str, optional): Application review ID to filter associated feature reviews.
        feature_review_id (str, optional): Unique feature review identifier.

    Returns:
        Tuple[Response, int]: JSON list of matching feature reviews and HTTP status 200.
    """
    app_review_id = request.args.get('app_review_id', '')
    feature_review_id = request.args.get('feature_review_id', '')

    if app_review_id:
        # Query database for all feature reviews tied to a specific app review
        feature_reviews = FeatureReviewDAO.query.filter_by(AppReviewID=app_review_id).all()
    elif feature_review_id:
        # Use modern db.session.get and filter out None if entity is not found
        feature_review = db.session.get(FeatureReviewDAO, feature_review_id)
        feature_reviews = [feature_review] if feature_review else []
    else:
        # Query database for all feature reviews
        feature_reviews = FeatureReviewDAO.query.all()

    result = feature_reviews_schema.dump(feature_reviews)
    return jsonify(result), 200


@feature_review_bp.route('/feature_review', methods=['POST'])
@api_required
def create_feature_review() -> Tuple[Response, int]:
    """
    Create a new feature review entry.

    Validates payload parameters, persists the entity in the database, and 
    returns the created object.

    Request Body (JSON):
        AppReviewID (str): Mandatory target application review identifier.
        Topic (str, optional): Subject or feature topic being evaluated.
        Score (float, optional): Numerical rating score.
        Comments (str, optional): Textual feedback content.

    Returns:
        Tuple[Response, int]: JSON serialized created feature review with HTTP 201 Created, 
                              or error response with HTTP status 400 or 500.
    """
    data = request.get_json() or {}

    # Validate mandatory payload fields
    if 'AppReviewID' not in data:
        return jsonify({'message': 'Missing required parameter: AppReviewID'}), 400

    # Instantiate new feature review entity
    feature_review = FeatureReviewDAO(
        AppReviewID=data['AppReviewID'],
        Topic=data.get('Topic'),
        Score=data.get('Score'),
        Comments=data.get('Comments')
    )

    try:
        db.session.add(feature_review)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({'message': 'Database error occurred while creating the feature review'}), 500

    result = feature_review_schema.dump(feature_review)
    return jsonify(result), 201


@feature_review_bp.route('/feature_review', methods=['DELETE'])
@api_required
def delete_feature_review() -> Union[Tuple[Response, int], Tuple[str, int]]:
    """
    Delete a feature review by its unique ID.

    Query Parameters:
        feature_review_id (str): Mandatory feature review ID to delete.

    Returns:
        Union[Tuple[Response, int], Tuple[str, int]]: Empty response with HTTP 204 No Content on success, 
                                                      HTTP 400 Bad Request if param is missing, 
                                                      HTTP 404 Not Found if record missing, 
                                                      or HTTP 500 on database failure.
    """
    feature_review_id = request.args.get('feature_review_id', '')

    # Missing query parameter is a client bad request (400)
    if not feature_review_id:
        return jsonify({'message': 'Parameter feature_review_id is required'}), 400

    # Query the feature review entity using modern SQLAlchemy syntax
    feature_review = db.session.get(FeatureReviewDAO, feature_review_id)

    if feature_review is None:
        return jsonify({'message': 'Feature review not found'}), 404

    try:
        db.session.delete(feature_review)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({'message': 'Database error occurred while deleting the feature review'}), 500

    return '', 204
