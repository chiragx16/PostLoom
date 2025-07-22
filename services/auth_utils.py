from flask_jwt_extended import jwt_required, get_jwt
from functools import wraps
from flask import jsonify

def role_required(required_roles):
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorated(*args, **kwargs):
            claims = get_jwt()
            if claims.get("role") not in (required_roles if isinstance(required_roles, list) else [required_roles]):
                return jsonify(msg="Insufficient access"), 403
            return fn(*args, **kwargs)
        return decorated
    return wrapper