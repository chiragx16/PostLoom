from flask import Blueprint
from .auth import auth_api
from .test import posts_api


api = Blueprint('api', __name__)

api.register_blueprint(auth_api, url_prefix='/api/auth')
api.register_blueprint(posts_api, url_prefix='/api/posts')

