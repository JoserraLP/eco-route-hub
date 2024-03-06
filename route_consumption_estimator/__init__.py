from flask import Flask
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy

from route_consumption_estimator.api.config import default
from route_consumption_estimator.static.constants import API_KEY

# Create the SQLAlchemy and Marshmallow objects
db = SQLAlchemy()
ma = Marshmallow()


def create_app():
    """
    Create A Flask app, configure it. register some project blueprints as 'auth' or 'main',
    initialize related services as MQTT or SQLAlchemy (with data insertion) and the flask login manager.

    Returns:
        app (object): Configured Flask app

    """
    # Create Flask app
    app = Flask(__name__, instance_relative_config=True)

    # Configure the application with the config file
    app.config.from_object(default)

    # Register project blueprints
    from route_consumption_estimator.api.blueprints.routes import routes_bp
    app.register_blueprint(routes_bp)

    from route_consumption_estimator.api.blueprints.users import users_bp
    app.register_blueprint(users_bp)

    from route_consumption_estimator.api.blueprints.user_vehicles import user_vehicles_bp
    app.register_blueprint(user_vehicles_bp)

    from route_consumption_estimator.api.blueprints.vehicles import vehicles_bp
    app.register_blueprint(vehicles_bp)

    from route_consumption_estimator.api.blueprints.user_stats import user_stats_bp
    app.register_blueprint(user_stats_bp)

    from route_consumption_estimator.api.blueprints.user_routes import user_routes_bp
    app.register_blueprint(user_routes_bp)

    from route_consumption_estimator.api.blueprints.app_review import app_review_bp
    app.register_blueprint(app_review_bp)

    from route_consumption_estimator.api.blueprints.feature_review import feature_review_bp
    app.register_blueprint(feature_review_bp)

    # Add app to db and ma
    db.init_app(app)
    ma.init_app(app)

    return app
