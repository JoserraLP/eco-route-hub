"""
App review route handlers.

Provides RESTful API endpoints for managing global application reviews, 
including listing/filtering reviews, creating new feedback entries, and 
deleting existing reviews.
"""

from typing import Tuple, Union
from flask import Blueprint, Response, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from route_consumption_estimator import db
from route_consumption_estimator.app.security import api_required
from route_consumption_estimator.domain.dao_models import AppReviewDAOSchema, AppReviewDAO

# Blueprint definition for application reviews
app_review_bp = Blueprint('app_review', __name__)

# Schema initializations for serialization and validation
app_review_schema = AppReviewDAOSchema()
app_reviews_schema = AppReviewDAOSchema(many=True)


@app_review_bp.route('/app_review', methods=['GET'])
@api_required
def get_app_reviews() -> Tuple[Response, int]:
    """
    Retrieve application reviews based on query filters.

    Supports fetching all reviews, filtering by user identifier, or querying 
    a single review by its unique ID.

    Query Parameters:
        user (str, optional): User ID to filter associated application reviews.
        app_review_id (str, optional): Unique review identifier.

    Returns:
        Tuple[Response, int]: JSON list containing matching application reviews and HTTP status 200.
    """
    user = request.args.get('user', '')
    app_review_id = request.args.get('app_review_id', '')

    if user:
        # Query database for all reviews submitted by the given user
        app_reviews = AppReviewDAO.query.filter_by(UserID=user).all()
    elif app_review_id:
        # Use modern db.session.get and filter out None if entity is not found
        review = db.session.get(AppReviewDAO, app_review_id)
        app_reviews = [review] if review else []
    else:
        # Query database for all existing application reviews
        app_reviews = AppReviewDAO.query.all()

    result = app_reviews_schema.dump(app_reviews)
    return jsonify(result), 200


@app_review_bp.route('/app_review', methods=['POST'])
@api_required
def create_app_review() -> Tuple[Response, int]:
    """
    Create a new application review entry.

    Validates payload parameters, persists the entity in the database, and 
    returns the created object.

    Request Body (JSON):
        UserID (str): Mandatory target user identifier.
        GlobalComments (str, optional): Textual review content.
        GlobalScore (float, optional): Numerical rating score.

    Returns:
        Tuple[Response, int]: JSON serialized created review with HTTP 201 Created, 
                              or error response with HTTP status 400 or 500.
    """
    data = request.get_json() or {}

    # Validate mandatory payload fields
    if 'UserID' not in data:
        return jsonify({'message': 'Missing required parameter: UserID'}), 400

    # Instantiate new application review entity
    app_review = AppReviewDAO(
        UserID=data['UserID'],
        GlobalComments=data.get('GlobalComments'),
        GlobalScore=data.get('GlobalScore')
    )

    try:
        db.session.add(app_review)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({'message': 'Database error occurred while creating the review'}), 500

    result = app_review_schema.dump(app_review)
    return jsonify(result), 201


@app_review_bp.route('/app_review', methods=['DELETE'])
@api_required
def delete_app_review() -> Union[Tuple[Response, int], Tuple[str, int]]:
    """
    Delete an application review by its unique ID.

    Query Parameters:
        app_review_id (str): Mandatory review ID to delete.

    Returns:
        Union[Tuple[Response, int], Tuple[str, int]]: Empty response with HTTP 204 No Content on success, 
                                                      HTTP 400 Bad Request if param is missing, 
                                                      HTTP 404 Not Found if record missing, 
                                                      or HTTP 500 on database failure.
    """
    app_review_id = request.args.get('app_review_id', '')

    # Missing query parameter is a client bad request (400)
    if not app_review_id:
        return jsonify({'message': 'Parameter app_review_id is required'}), 400

    # Query the review entity using modern SQLAlchemy syntax
    app_review = db.session.get(AppReviewDAO, app_review_id)

    if app_review is None:
        return jsonify({'message': 'App review not found'}), 404

    try:
        db.session.delete(app_review)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({'message': 'Database error occurred while deleting the review'}), 500

    return '', 204
