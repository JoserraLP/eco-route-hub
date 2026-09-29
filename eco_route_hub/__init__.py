"""
Application factory module for the Route Consumption Estimator.

This module is responsible for bootstrapping the Flask application, loading
configurations, initializing the plugin system, configuring extensions
(SQLAlchemy, Marshmallow), and registering all application blueprints.
"""

from typing import Union
from dotenv import load_dotenv
from flask import Flask

from eco_route_hub.config.models import AppConfig
from eco_route_hub.extensions import db, ma

from eco_route_hub.config.loader import load_config
from eco_route_hub.core.plugin_manager import PluginManager

from pathlib import Path

# Base package directory
PACKAGE_DIR = Path(__file__).parent.resolve()

# Default configuration file path
CONFIG_FILE_DIR = PACKAGE_DIR / "config" / "config_base.yaml"

# Load environment variables from a .env file
load_dotenv()


def create_app(config_dir: Union[str, Path] = CONFIG_FILE_DIR) -> Flask:
    """
    Create and configure an instance of the Flask application.

    This factory function initializes the app context, loads the application
    configuration, sets up the custom plugin system, configures database and
    serialization extensions, and registers all modular routing blueprints.

    Args:
        config_dir (Union[str, Path], optional): The path to the configuration 
            directory. Defaults to `CONFIG_FILE_DIR`.

    Returns:
        Flask: The fully configured Flask application instance.
    """

    # Load configuration from the specified directory
    app_config = load_config(config_dir)

    # Initialize and load the custom plugin system
    manager = PluginManager(app_config)
    manager.load()

    # Create the Flask application instance
    app = Flask(__name__, instance_relative_config=True)

    # Store typed configurations and plugin properties inside the Flask app context
    app.config["APP_CONFIG"] = app_config
    app.config["ALL_ATTRIBUTES"] = manager.all_attributes

    # Configure the SQLAlchemy database connection and behavior
    app.config["SQLALCHEMY_DATABASE_URI"] = app_config.system.database.get("sqlalchemy_database_uri")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = app_config.system.database.get(
        "sqlalchemy_track_modifications", False
    )

    # Store the plugin registry inside the app context for global access
    app.config["PLUGIN_REGISTRY"] = manager.registry

    # Initialize Flask extensions with the app instance
    db.init_app(app)
    ma.init_app(app)

    # -------------------------------------------------------------------------
    # Blueprint Registration
    # -------------------------------------------------------------------------

    from eco_route_hub.app.routes.routes import routes_bp
    app.register_blueprint(routes_bp)

    from eco_route_hub.app.routes.users import users_bp
    app.register_blueprint(users_bp)

    from eco_route_hub.app.routes.user_vehicles import user_vehicles_bp
    app.register_blueprint(user_vehicles_bp)

    from eco_route_hub.app.routes.vehicles import vehicles_bp
    app.register_blueprint(vehicles_bp)

    from eco_route_hub.app.routes.user_stats import user_stats_bp
    app.register_blueprint(user_stats_bp)

    from eco_route_hub.app.routes.user_routes import user_routes_bp
    app.register_blueprint(user_routes_bp)

    from eco_route_hub.app.routes.app_review import app_review_bp
    app.register_blueprint(app_review_bp)

    from eco_route_hub.app.routes.feature_review import feature_review_bp
    app.register_blueprint(feature_review_bp)

    from eco_route_hub.app.routes.benchmarking import benchmarking_bp
    app.register_blueprint(benchmarking_bp)

    return app
