# TODO: move general helper functions from functions.py into this module
from functools import wraps
from flask import jsonify

def error_handler(func):
    @wraps(func)  # ✅ preserves function name, docstring, etc.
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Error occurred in {func.__name__}: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 400  # ✅ always return status code
    return wrapper
