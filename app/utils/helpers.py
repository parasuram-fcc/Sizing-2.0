# TODO: move general helper functions from functions.py into this module
from functools import wraps
import traceback
from flask import jsonify

def error_handler(func):
    @wraps(func)  # ✅ preserves function name, docstring, etc.
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Error occurred in {func.__name__}: {e}")
            traceback.print_exc()
            return jsonify({
                'status': 'error',
                'message': 'something went wrong',
                'error':str(e)
            }), 400  # ✅ always return status code
    return wrapper
