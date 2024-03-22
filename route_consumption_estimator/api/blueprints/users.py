from flask import Blueprint, jsonify, request
from route_consumption_estimator.api.models import *
from route_consumption_estimator.api.security import api_required

# users blueprint
users_bp = Blueprint('users', __name__)

# Create the User schema objects
user_schema = UserSchema()
users_schema = UserSchema(many=True)


# Create an endpoint to get all or filtered by email users
@users_bp.route('/users', methods=['GET'])
@api_required
def get_users():
    # Retrieve query params (email)
    email = request.args.get('email', '')
    if email:
        # Query the database for the user with the given email
        users = User.query.filter_by(Email=email)
    else:
        # Query the database for all users
        users = User.query.all()

    # Serialize the users as JSON
    result = users_schema.dump(users)
    # Return the JSON response
    return jsonify(result)


# Create an endpoint to create a new user
@users_bp.route('/users', methods=['POST'])
@api_required
def create_user():
    # Get the JSON data from the request
    data = request.get_json()
    # Validate the data
    if 'Name' not in data or 'Email' not in data or 'Password' not in data:
        # Return A 400 bad request error
        return jsonify({'message': 'Missing data'}), 400
    # Create new user object
    user = User(Name=data.get('Name'), Email=data.get('Email'), Password=data.get('Password'),
                BirthDate=data.get('BirthDate'), Gender=data.get('Gender'),
                DrivingLicenseYear=data.get('DrivingLicenseYear'))
    # Add the user to the database
    db.session.add(user)
    db.session.commit()
    # Serialize the user as JSON
    result = user_schema.dump(user)
    # Return the JSON response with A 201 created status
    return jsonify(result), 201


# Create an endpoint to update a user vehicle by user ID
@users_bp.route('/users', methods=['PUT'])
@api_required
def update_user(user_id):
    # Get the JSON data from the request
    data = request.get_json()
    user_id = data.get('UserID')
    # Check if the parameter not set
    if not user_id:
        # Return A 404 not found error
        return jsonify({'message': 'UserID is required'}), 404
    # Query the database for the user with the given ID
    user = User.query.get(user_id)
    # Check if the user exists
    if user is None:
        # Return A 404 not found error
        return jsonify({'message': 'User not found'}), 404

    # Update the user attributes
    user.Name = data.get('Name', user.Name)
    user.Email = data.get('Email', user.Email)
    user.Password = data.get('Password', user.Password)
    user.BirthDate = data.get('BirthDate', user.BirthDate)
    user.Gender = data.get('Gender', user.Gender)
    user.DrivingLicenseYear = data.get('DrivingLicenseYear', user.DrivingLicenseYear)

    # Commit the changes to the database
    db.session.commit()
    # Serialize the user as JSON
    result = user_schema.dump(user)
    # Return the JSON response
    return jsonify(result)


# Create an endpoint to remove a specific user
@users_bp.route('/users', methods=['DELETE'])
@api_required
def delete_user():
    user_id = request.args.get('user_id', '')
    # Check if the parameter not set
    if not user_id:
        # Return A 404 not found error
        return jsonify({'message': 'user_id is required'}), 404
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
