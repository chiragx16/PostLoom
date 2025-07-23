from services.auth_utils import role_required
from flask import request, jsonify, Blueprint
from models import User
from services.redis_store import redis_client
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from datetime import datetime


posts_api = Blueprint('posts_api',__name__)



# Routes
@posts_api.route('/users', methods=['GET'])
@jwt_required()
@role_required(["editor", "author"])
def get_users():

    jti = get_jwt()["jti"]
    user_id = get_jwt_identity()
    now = datetime.utcnow().isoformat()

    redis_client.hset(f"session_{user_id}_{jti}", "last_active", now)


    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

# @app.route('/users', methods=['POST'])
# def create_user():
#     data = request.get_json()
    
#     if not data or 'username' not in data or 'email' not in data:
#         return jsonify({'error': 'Username and email are required'}), 400
    
#     # Check if user already exists
#     if User.query.filter_by(username=data['username']).first():
#         return jsonify({'error': 'Username already exists'}), 400
    
#     if User.query.filter_by(email=data['email']).first():
#         return jsonify({'error': 'Email already exists'}), 400
    
#     user = User(username=data['username'], email=data['email'])
#     db.session.add(user)
#     db.session.commit()
    
#     return jsonify(user.to_dict()), 201

# @app.route('/users/<int:user_id>', methods=['GET'])
# def get_user(user_id):
#     user = User.query.get_or_404(user_id)
#     return jsonify(user.to_dict())

# @app.route('/users/<int:user_id>', methods=['PUT'])
# def update_user(user_id):
#     user = User.query.get_or_404(user_id)
#     data = request.get_json()
    
#     if 'username' in data:
#         user.username = data['username']
#     if 'email' in data:
#         user.email = data['email']
    
#     db.session.commit()
#     return jsonify(user.to_dict())

# @app.route('/users/<int:user_id>', methods=['DELETE'])
# def delete_user(user_id):
#     user = User.query.get_or_404(user_id)
#     db.session.delete(user)
#     db.session.commit()
#     return jsonify({'message': 'User deleted successfully'})

# @app.route('/posts', methods=['GET'])
# def get_posts():
#     posts = Post.query.all()
#     return jsonify([post.to_dict() for post in posts])

# @app.route('/posts', methods=['POST'])
# def create_post():
#     data = request.get_json()
    
#     if not data or 'title' not in data or 'content' not in data or 'user_id' not in data:
#         return jsonify({'error': 'Title, content, and user_id are required'}), 400
    
#     # Check if user exists
#     user = User.query.get(data['user_id'])
#     if not user:
#         return jsonify({'error': 'User not found'}), 404
    
#     post = Post(title=data['title'], content=data['content'], user_id=data['user_id'])
#     db.session.add(post)
#     db.session.commit()
    
#     return jsonify(post.to_dict()), 201