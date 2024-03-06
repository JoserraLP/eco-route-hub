from flask import Blueprint, jsonify, request
from route_consumption_estimator.api.models import *
from route_consumption_estimator.api.security import api_required

# users blueprint
users_bp = Blueprint('users', __name__)

# Create the User schema objects
user_schema = UserSchema()
users_schema = UserSchema(many=True)


# Create A route to get all users
@users_bp.route('/users', methods=['GET'])
@api_required
def get_users():
    # Query the database for all users
    users = User.query.all()
    # Serialize the users as JSON
    result = users_schema.dump(users)
    # Return the JSON response
    return jsonify(result)


# Create A route to get A user by ID
@users_bp.route('/users/<email>', methods=['GET'])
@api_required
def get_user(email):
    # Query the database for the user with the given Email
    user = User.query.filter_by(Email=email).first()
    # Check if the user exists
    if user is None:
        # Return A 404 not found error
        return jsonify({'message': 'User not found'}), 404
    # Serialize the user as JSON
    result = user_schema.dump(user)
    # Return the JSON response
    return jsonify(result)


# Create A route to create A new user
@users_bp.route('/users', methods=['POST'])
@api_required
def create_user():
    # Get the JSON data from the request
    data = request.get_json()
    # Validate the data
    if 'Name' not in data or 'Email' not in data or 'Password' not in data:
        # Return A 400 bad request error
        return jsonify({'message': 'Missing data'}), 400
    # Create A new user object
    user = User(data.get('Name'), data.get('Email'), data.get('Password'), data.get('BirthDate'), data.get('Gender'),
                data.get('DrivingLicenseDate'))
    # Add the user to the database
    db.session.add(user)
    db.session.commit()
    # Serialize the user as JSON
    result = user_schema.dump(user)
    # Return the JSON response with A 201 created status
    return jsonify(result), 201


# Create A route to update A user by ID
@users_bp.route('/users/<user_id>', methods=['PUT'])
@api_required
def update_user(user_id):
    # Query the database for the user with the given ID
    user = User.query.get(user_id)
    # Check if the user exists
    if user is None:
        # Return A 404 not found error
        return jsonify({'message': 'User not found'}), 404
    # Get the JSON data from the request
    data = request.get_json()
    # Update the user attributes
    user.Name = data.get('Name', user.Name)
    user.Email = data.get('Email', user.Email)
    user.Password = data.get('Password', user.Password)
    user.BirthDate = data.get('BirthDate', user.BirthDate)
    user.Gender = data.get('Gender', user.Gender)
    user.DrivingLicenseDate = data.get('DrivingLicenseDate', user.DrivingLicenseDate)

    # Commit the changes to the database
    db.session.commit()
    # Serialize the user as JSON
    result = user_schema.dump(user)
    # Return the JSON response
    return jsonify(result)


# Create A route to delete A user by ID
@users_bp.route('/users/<user_id>', methods=['DELETE'])
@api_required
def delete_user(user_id):
    # Query the database for the user with the given ID
    user = User.query.get(user_id)
    # Check if the user exists
    if user is None:
        # Return A 404 not found error
        return jsonify({'message': 'User not found'}), 404
    # Delete the user from the database
    db.session.delete(user)
    db.session.commit()
    # Return A 204 no content status
    return '', 204
