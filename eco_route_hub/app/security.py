"""
Security and authentication module for the application.

Provides utility functions and decorators to enforce API key authorization 
and access control on Flask routes.
"""

import functools
from typing import Any, Callable, Dict, Optional, Tuple, Union
from flask import current_app, request


def is_valid(api_key: Optional[str]) -> bool:
    """
    Validate a provided API key against the configured system API key.

    Args:
        api_key (Optional[str]): The API key string received from the incoming request.

    Returns:
        bool: True if the provided key matches the application configuration, 
              False otherwise.
    """
    current_app_config = current_app.config["APP_CONFIG"].system
    return api_key == current_app_config.api_key


def api_required(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator for Flask view functions to enforce API key authentication.

    Checks for an `api_key` parameter in the query string (`request.args`).
    If missing, returns a 400 Bad Request error response.
    If invalid, returns a 403 Forbidden error response.

    Args:
        func (Callable[..., Any]): The Flask view function to protect.

    Returns:
        Callable[..., Any]: The wrapped decorated function.
    """
    @functools.wraps(func)
    def decorator(*args: Any, **kwargs: Any) -> Union[Tuple[Dict[str, str], int], Any]:
        # Extract API key from query parameters
        if request.args:
            api_key = request.args.get("api_key")
        else:
            return {"message": "Please provide an API key"}, 400

        # Check if API key is correct and valid
        if is_valid(api_key):
            return func(*args, **kwargs)
        else:
            return {"message": "The provided API key is not valid"}, 403

    return decorator
