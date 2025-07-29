from flask import Blueprint, request, jsonify, make_response, g, redirect, url_for
from flask_jwt_extended import create_access_token
from flask_jwt_extended import jwt_required, get_jwt
from flask_jwt_extended import get_jwt_identity, decode_token
from werkzeug.security import check_password_hash
from services.redis_store import redis_client  
from services.auth_utils import jwt_required_cookie
from models import User
from datetime import timedelta, datetime

auth_api = Blueprint('auth_api',__name__)


@auth_api.route("/check-auth", methods=["GET"])
@jwt_required_cookie
def check_auth():
    return jsonify({"message": "Already authenticated"}), 200


@auth_api.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data["email"]).first()
    
    if not user or not user.check_password(data["password"]):  # Add password validation
        return jsonify({"message": "Invalid credentials"}), 401

    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role}
    )

    # Session metadata
    decoded = decode_token(token)
    jti = decoded["jti"]
    device = request.headers.get("User-Agent")[:128] or "Unknown"
    ip = request.remote_addr or "Unknown"
    timestamp = datetime.utcnow().isoformat()

    session_key = f"session_{user.id}_{jti}"
    redis_client.hmset(session_key, {
        "device": device,
        "ip": ip,
        "created_at": timestamp,
        "last_active": timestamp
    })
    redis_client.expire(session_key, timedelta(hours=2))

    # Create response and set cookie
    response = make_response(jsonify({
        "message": "Login successful",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role
        }
    }))
    
    # Set HTTP-only cookie for security
    response.set_cookie(
        'auth_token',
        token,
        max_age=timedelta(hours=2),  # Cookie expires in 7 days
        httponly=True,              # Prevents XSS attacks
        secure=True,                # Only send over HTTPS
        samesite='Strict'           # CSRF protection
    )
    
    return response



@auth_api.route("/logout", methods=["POST"])
@jwt_required_cookie
def logout():
    # Get token to invalidate session
    current_user_id = g.current_user_id
    token = request.cookies.get('auth_token')
    if token:
        try:
            decoded = decode_token(token)
            jti = decoded["jti"]
            session_key = f"session_{current_user_id}_{jti}"
            redis_client.delete(session_key)  # Remove from Redis
        except:
            pass  # Token might be invalid, but still clear cookie
    
    response = make_response(redirect(url_for("api.posts_api.login_page")))
    response.set_cookie('auth_token', '', expires=0)  # Clear cookie
    return response





@auth_api.route("/sessions", methods=["GET"])
@jwt_required()
def list_sessions():
    user_id = get_jwt_identity()
    keys = redis_client.keys(f"session_{user_id}_*")
    
    sessions = []
    for key in keys:
        decoded_key = key.decode()
        data = redis_client.hgetall(key)
        jti = decoded_key.split("_")[-1]
        revoked = redis_client.exists(f"revoked_{jti}")
        ttl_seconds = redis_client.ttl(f"session_{user_id}_{jti}")
        expires_at = (
            datetime.utcnow() + timedelta(seconds=ttl_seconds)
        ).isoformat() if ttl_seconds > 0 else "expired"

        sessions.append({
            "jti": jti,
            "device": data.get(b"device", b"").decode(),
            "ip": data.get(b"ip", b"").decode(),
            "created_at": data.get(b"created_at", b"").decode(),
            "last_active": data.get(b"last_active", b"").decode(),
            "revoked": bool(revoked),
            "expires_at": expires_at
        })

    
    return jsonify(sessions=sessions)




@auth_api.route("/revoke-session/<jti>", methods=["POST"])
@jwt_required()
def revoke_session(jti):
    user_id = get_jwt_identity()

    session_key = f"session_{user_id}_{jti}"
    if not redis_client.exists(session_key):
        return jsonify({"msg": "Session not found"}), 404

    # Revoke the token
    redis_client.setex(f"revoked_{jti}", timedelta(hours=2), "revoked")

    # Delete session metadata
    redis_client.delete(session_key)

    return jsonify({"msg": f"Session {jti} revoked successfully."})




@auth_api.route("/logout_all", methods=["GET"])
@jwt_required()
def logout_all():
    user_id = get_jwt_identity()
    keys = redis_client.keys(f"session_{user_id}_*")
    for key in keys:
        jti = key.decode().split("_")[-1]
        redis_client.setex(f"revoked_{jti}", timedelta(hours=2), "revoked")
        redis_client.delete(key)
    return jsonify(msg="Logged out from all sessions")