from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
import re

# Initialize Flask app
app = Flask(__name__)

# Database configuration
DB_USER = 'your_username'
DB_PASSWORD = 'your_password'
DB_HOST = 'localhost'
DB_PORT = '3306'
DB_NAME = 'your_database_name'

# SQLAlchemy configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Association table for many-to-many relationship between Post and Tag
post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default="author")  # "author", "editor", "admin"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    posts = db.relationship("Post", backref="author", lazy=True)
    comments = db.relationship("Comment", backref="user", lazy=True)
    uploaded_media = db.relationship("MediaAsset", backref="uploader", lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'posts_count': len(self.posts)
        }

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    posts = db.relationship("Post", backref="category", lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'posts_count': len(self.posts)
        }

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'posts_count': len(self.posts)
        }

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    body_md = db.Column(db.Text, nullable=False)
    body_html = db.Column(db.Text)
    status = db.Column(db.String(50), default="draft")  # draft, pending, published, archived
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"))
    
    versions = db.relationship("PostVersion", backref="post", lazy=True, cascade="all, delete-orphan")
    tags = db.relationship("Tag", secondary=post_tags, backref="posts")
    comments = db.relationship("Comment", backref="post", lazy=True, cascade="all, delete-orphan")
    analytics = db.relationship("PostAnalytics", backref="post", uselist=False, cascade="all, delete-orphan")
    media_assets = db.relationship("MediaAsset", backref="post", lazy=True)
    
    def generate_slug(self):
        """Generate URL-friendly slug from title"""
        if self.title:
            slug = re.sub(r'[^\w\s-]', '', self.title.lower())
            slug = re.sub(r'[-\s]+', '-', slug).strip('-')
            return slug
        return ''
    
    def create_version(self):
        """Create a new version when post is updated"""
        version_count = PostVersion.query.filter_by(post_id=self.id).count()
        version = PostVersion(
            post_id=self.id,
            version_number=version_count + 1,
            body_md=self.body_md
        )
        db.session.add(version)
        return version
    
    def to_dict(self, include_body=False):
        data = {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'author': self.author.username if self.author else None,
            'category': self.category.name if self.category else None,
            'tags': [tag.name for tag in self.tags],
            'comments_count': len(self.comments),
            'versions_count': len(self.versions)
        }
        
        if include_body:
            data['body_md'] = self.body_md
            data['body_html'] = self.body_html
            
        if self.analytics:
            data['analytics'] = self.analytics.to_dict()
            
        return data

class PostVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    body_md = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'post_id': self.post_id,
            'version_number': self.version_number,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("comment.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    replies = db.relationship("Comment", backref=db.backref("parent", remote_side=[id]), lazy=True)
    
    def to_dict(self, include_replies=False):
        data = {
            'id': self.id,
            'post_id': self.post_id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'body': self.body,
            'parent_id': self.parent_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'replies_count': len(self.replies)
        }
        
        if include_replies:
            data['replies'] = [reply.to_dict() for reply in self.replies]
            
        return data

class PostAnalytics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), unique=True, nullable=False)
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    read_time_seconds = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def increment_views(self):
        self.views += 1
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def increment_likes(self):
        self.likes += 1
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self):
        return {
            'id': self.id,
            'post_id': self.post_id,
            'views': self.views,
            'likes': self.likes,
            'read_time_seconds': self.read_time_seconds,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class MediaAsset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'filepath': self.filepath,
            'uploaded_by': self.uploader.username if self.uploader else None,
            'post_id': self.post_id,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None
        }

class Subscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'active': self.active,
            'subscribed_at': self.subscribed_at.isoformat() if self.subscribed_at else None
        }

# API Routes

# User routes
@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    
    required_fields = ['username', 'email', 'password']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Username, email, and password are required'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    user = User(
        username=data['username'],
        email=data['email'],
        role=data.get('role', 'author')
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify(user.to_dict()), 201

# Post routes
@app.route('/posts', methods=['GET'])
def get_posts():
    status = request.args.get('status', 'published')
    category_id = request.args.get('category_id')
    author_id = request.args.get('author_id')
    
    query = Post.query
    
    if status != 'all':
        query = query.filter_by(status=status)
    if category_id:
        query = query.filter_by(category_id=category_id)
    if author_id:
        query = query.filter_by(author_id=author_id)
    
    posts = query.order_by(Post.created_at.desc()).all()
    return jsonify([post.to_dict() for post in posts])

@app.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Increment view count
    if not post.analytics:
        analytics = PostAnalytics(post_id=post.id)
        db.session.add(analytics)
        db.session.commit()
        post.analytics = analytics
    
    post.analytics.increment_views()
    
    return jsonify(post.to_dict(include_body=True))

@app.route('/posts', methods=['POST'])
def create_post():
    data = request.get_json()
    
    required_fields = ['title', 'body_md', 'author_id']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Title, body_md, and author_id are required'}), 400
    
    # Check if author exists
    author = User.query.get(data['author_id'])
    if not author:
        return jsonify({'error': 'Author not found'}), 404
    
    post = Post(
        title=data['title'],
        body_md=data['body_md'],
        body_html=data.get('body_html', ''),
        author_id=data['author_id'],
        category_id=data.get('category_id'),
        status=data.get('status', 'draft')
    )
    
    # Generate slug if not provided
    post.slug = data.get('slug', post.generate_slug())
    
    # Check if slug is unique
    existing_post = Post.query.filter_by(slug=post.slug).first()
    if existing_post:
        post.slug = f"{post.slug}-{datetime.utcnow().timestamp()}"
    
    db.session.add(post)
    db.session.commit()
    
    # Create initial analytics record
    analytics = PostAnalytics(post_id=post.id)
    db.session.add(analytics)
    
    # Handle tags
    if 'tags' in data:
        for tag_name in data['tags']:
            tag = Tag.query.filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.session.add(tag)
            post.tags.append(tag)
    
    db.session.commit()
    
    return jsonify(post.to_dict(include_body=True)), 201

@app.route('/posts/<int:post_id>', methods=['PUT'])
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    data = request.get_json()
    
    # Create version before updating
    post.create_version()
    
    # Update fields
    if 'title' in data:
        post.title = data['title']
        if 'slug' not in data:
            post.slug = post.generate_slug()
    
    if 'slug' in data:
        post.slug = data['slug']
    
    if 'body_md' in data:
        post.body_md = data['body_md']
    
    if 'body_html' in data:
        post.body_html = data['body_html']
    
    if 'status' in data:
        post.status = data['status']
    
    if 'category_id' in data:
        post.category_id = data['category_id']
    
    # Handle tags update
    if 'tags' in data:
        post.tags.clear()
        for tag_name in data['tags']:
            tag = Tag.query.filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.session.add(tag)
            post.tags.append(tag)
    
    post.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify(post.to_dict(include_body=True))

# Comment routes
@app.route('/posts/<int:post_id>/comments', methods=['GET'])
def get_post_comments(post_id):
    post = Post.query.get_or_404(post_id)
    # Get only top-level comments (no parent)
    comments = Comment.query.filter_by(post_id=post_id, parent_id=None).order_by(Comment.created_at.desc()).all()
    return jsonify([comment.to_dict(include_replies=True) for comment in comments])

@app.route('/comments', methods=['POST'])
def create_comment():
    data = request.get_json()
    
    required_fields = ['post_id', 'user_id', 'body']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'post_id, user_id, and body are required'}), 400
    
    comment = Comment(
        post_id=data['post_id'],
        user_id=data['user_id'],
        body=data['body'],
        parent_id=data.get('parent_id')
    )
    
    db.session.add(comment)
    db.session.commit()
    
    return jsonify(comment.to_dict()), 201

# Analytics routes
@app.route('/posts/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    if not post.analytics:
        analytics = PostAnalytics(post_id=post.id)
        db.session.add(analytics)
        db.session.commit()
        post.analytics = analytics
    
    post.analytics.increment_likes()
    
    return jsonify({'message': 'Post liked', 'likes': post.analytics.likes})

# Category and Tag routes
@app.route('/categories', methods=['GET'])
def get_categories():
    categories = Category.query.all()
    return jsonify([category.to_dict() for category in categories])

@app.route('/categories', methods=['POST'])
def create_category():
    data = request.get_json()
    
    if 'name' not in data:
        return jsonify({'error': 'Name is required'}), 400
    
    category = Category(name=data['name'])
    db.session.add(category)
    db.session.commit()
    
    return jsonify(category.to_dict()), 201

@app.route('/tags', methods=['GET'])
def get_tags():
    tags = Tag.query.all()
    return jsonify([tag.to_dict() for tag in tags])

# Subscriber routes
@app.route('/subscribers', methods=['POST'])
def create_subscriber():
    data = request.get_json()
    
    if 'email' not in data:
        return jsonify({'error': 'Email is required'}), 400
    
    if Subscriber.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already subscribed'}), 400
    
    subscriber = Subscriber(email=data['email'])
    db.session.add(subscriber)
    db.session.commit()
    
    return jsonify(subscriber.to_dict()), 201

# Initialize database
def init_db():
    with app.app_context():
        db.create_all()
        print("Database tables created!")

if __name__ == '__main__':
    # Uncomment to initialize database
    # init_db()
    app.run(debug=True)