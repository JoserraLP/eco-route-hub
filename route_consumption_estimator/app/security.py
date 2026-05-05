import functools

from flask import request, current_app


def is_valid(api_key):
    current_app_config = current_app.config["APP_CONFIG"].system
    return api_key == current_app_config.api_key


def api_required(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
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
