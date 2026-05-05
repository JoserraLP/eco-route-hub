from dotenv import load_dotenv
from flask import Flask
from route_consumption_estimator.extensions import db, ma

from route_consumption_estimator.config.loader import load_config
from route_consumption_estimator.core.plugin_manager import PluginManager

load_dotenv()


def create_app():
    """
    Create A Flask app, configure it. register some project routes as 'auth' or 'main',
    initialize related services as MQTT or SQLAlchemy (with data insertion) and the flask login manager.

    Returns:
        app (object): Configured Flask app

    """

    app_config = load_config()
    # Initialize plugin system
    manager = PluginManager(app_config)

    manager.load()

    # Create Flask app
    app = Flask(__name__, instance_relative_config=True)

    # Store typed config inside Flask
    app.config["APP_CONFIG"] = app_config

    # Configure single database into flask app

    app.config["SQLALCHEMY_DATABASE_URI"] = app_config.system.database.get("sqlalchemy_database_uri")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = app_config.system.database.get(
        "sqlalchemy_track_modifications", False
    )

    # Store registry inside app context
    app.config["PLUGIN_REGISTRY"] = manager.registry

    db.init_app(app)
    ma.init_app(app)

    # Register project routes
    from route_consumption_estimator.app.routes.routes import routes_bp
    app.register_blueprint(routes_bp)

    from route_consumption_estimator.app.routes.users import users_bp
    app.register_blueprint(users_bp)

    from route_consumption_estimator.app.routes.user_vehicles import user_vehicles_bp
    app.register_blueprint(user_vehicles_bp)

    from route_consumption_estimator.app.routes.vehicles import vehicles_bp
    app.register_blueprint(vehicles_bp)

    from route_consumption_estimator.app.routes.user_stats import user_stats_bp
    app.register_blueprint(user_stats_bp)

    from route_consumption_estimator.app.routes.user_routes import user_routes_bp
    app.register_blueprint(user_routes_bp)

    from route_consumption_estimator.app.routes.app_review import app_review_bp
    app.register_blueprint(app_review_bp)

    from route_consumption_estimator.app.routes.feature_review import feature_review_bp
    app.register_blueprint(feature_review_bp)

    return app
