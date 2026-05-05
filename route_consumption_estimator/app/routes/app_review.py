from flask import Blueprint, jsonify, request
from route_consumption_estimator.domain import *
from route_consumption_estimator.app.security import api_required

# app_review blueprint
app_review_bp = Blueprint('app_review', __name__)

# Create the AppReview schema objects
app_review_schema = AppReviewDAOSchema()
app_reviews_schema = AppReviewDAOSchema(many=True)


# Create an endpoint to get all or filtered app_reviews
@app_review_bp.route('/app_review', methods=['GET'])
@api_required
def get_app_reviews():
    # Retrieve query params (user, app_review_id)
    user = request.args.get('user', '')
    app_review_id = request.args.get('app_review_id', '')
    if user:
        # Query the database for the user application reviews
        app_reviews = AppReviewDAO.query.filter_by(UserID=user)
    elif app_review_id:
        # Query the database for a specific application review (included in a list to fit the output schema)
        app_reviews = [AppReviewDAO.query.get(app_review_id)]
    else:
        # Query the database for all app reviews
        app_reviews = AppReviewDAO.query.all()

    result = app_reviews_schema.dump(app_reviews)
    # Return the JSON response
    return jsonify(result)


# Create an endpoint to create a new app review
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
    app_review = AppReviewDAO(UserID=data['UserID'], GlobalComments=data.get('GlobalComments'),
                              GlobalScore=data.get('GlobalScore'))
    # Add the app review to the database
    db.session.add(app_review)
    db.session.commit()
    # Serialize the app review as JSON
    result = app_review_schema.dump(app_review)
    # Return the JSON response with A 201 created status
    return jsonify(result), 201


# Create an endpoint to delete an app review by ID
@app_review_bp.route('/app_review', methods=['DELETE'])
@api_required
def delete_app_review():
    # Retrieve query params (user, app_review_id)
    app_review_id = request.args.get('app_review_id', '')
    # Check if the parameter not set
    if not app_review_id:
        # Return A 404 not found error
        return jsonify({'message': 'app_review_id is required'}), 404

    # Query the database for the app review with the given ID
    app_review = AppReviewDAO.query.get(app_review_id)

    # Check if the app review exists
    if app_review is None:
        # Return A 404 not found error
        return jsonify({'message': 'App review not found'}), 404
    # Delete the app review from the database
    db.session.delete(app_review)
    db.session.commit()
    # Return A 204 no content status
    return '', 204
