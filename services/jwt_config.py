from flask_jwt_extended import JWTManager
from datetime import timedelta
from services.redis_store import redis_client  

jwt = JWTManager()

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    entry = redis_client.get(f"revoked_{jti}")
    return entry is not None

def configure_jwt(app):
    jwt.init_app(app)