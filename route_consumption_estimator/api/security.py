from flask import request

from route_consumption_estimator import API_KEY
import functools


def is_valid(api_key):
    return api_key == API_KEY


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
