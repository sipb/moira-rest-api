from flask import jsonify

def json_api(func):
    def decorated(*args, **kwargs):
        return jsonify(func(*args, **kwargs))
    return decorated

