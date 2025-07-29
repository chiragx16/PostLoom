from flask_jwt_extended import jwt_required, get_jwt
from functools import wraps
from flask import request, jsonify, current_app
import jwt
from datetime import datetime

from services.redis_store import redis_client  

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




# def jwt_required_cookie(f):
#     @wraps(f)
#     def decorated(*args, **kwargs):
#         token = None
        
#         # Check for token in cookie first, then Authorization header
#         if 'auth_token' in request.cookies:
#             token = request.cookies['auth_token']
#         elif 'Authorization' in request.headers:
#             auth_header = request.headers['Authorization']
#             try:
#                 token = auth_header.split(" ")[1]  # Bearer <token>
#             except IndexError:
#                 return jsonify({'message': 'Invalid token format'}), 401
        
#         if not token:
#             return jsonify({'message': 'Token is missing'}), 401
        
#         try:
#             # Decode and verify token
#             data = jwt.decode(
#                 token, 
#                 current_app.config['JWT_SECRET_KEY'], 
#                 algorithms=["HS256"]
#             )
#             current_user_id = data['sub']
            
#             # Update last active time in Redis
#             jti = data['jti']
#             session_key = f"session_{current_user_id}_{jti}"
#             if redis_client.exists(session_key):
#                 redis_client.hset(session_key, "last_active", datetime.utcnow().isoformat())
#             else:
#                 return jsonify({'message': 'Session expired'}), 401
                
#         except jwt.ExpiredSignatureError:
#             return jsonify({'message': 'Token has expired'}), 401
#         except jwt.InvalidTokenError:
#             return jsonify({'message': 'Invalid token'}), 401
        
#         return f(current_user_id, *args, **kwargs)
    
#     return decorated


from flask import g

def jwt_required_cookie(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'auth_token' in request.cookies:
            token = request.cookies['auth_token']
        elif 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                return jsonify({'message': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            data = jwt.decode(
                token, 
                current_app.config['JWT_SECRET_KEY'], 
                algorithms=["HS256"]
            )
            g.current_user_id = data['sub']  # ✅ save in global context
            
            jti = data['jti']
            session_key = f"session_{g.current_user_id}_{jti}"
            if redis_client.exists(session_key):
                redis_client.hset(session_key, "last_active", datetime.utcnow().isoformat())
            else:
                return jsonify({'message': 'Session expired'}), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
        
        return f(*args, **kwargs)  # ✅ don't inject as argument
    
    return decorated
