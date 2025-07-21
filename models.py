from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import re
import uuid

# Initialize SQLAlchemy
db = SQLAlchemy()


# Association table for many-to-many relationship between Post and Tag
post_tags = db.Table('post_tags',
    db.Column('post_id', db.String(36), db.ForeignKey('post.id'), primary_key=True),
    db.Column('tag_id', db.String(36), db.ForeignKey('tag.id'), primary_key=True)
)

# Models
class User(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
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
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    posts = db.relationship("Post", backref="category", lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'posts_count': len(self.posts)
        }

class Tag(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'posts_count': len(self.posts)
        }

class Post(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    body_md = db.Column(db.Text, nullable=False)
    body_html = db.Column(db.Text)
    status = db.Column(db.String(50), default="draft")  # draft, pending, published, archived
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    author_id = db.Column(db.String(36), db.ForeignKey("user.id"), nullable=False)
    category_id = db.Column(db.String(36), db.ForeignKey("category.id"))
    
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
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = db.Column(db.String(36), db.ForeignKey("post.id"), nullable=False)
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
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = db.Column(db.String(36), db.ForeignKey("post.id"), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.String(36), db.ForeignKey("comment.id"), nullable=True)
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
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = db.Column(db.String(36), db.ForeignKey("post.id"), unique=True, nullable=False)
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
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    uploaded_by = db.Column(db.String(36), db.ForeignKey("user.id"), nullable=False)
    post_id = db.Column(db.String(36), db.ForeignKey("post.id"))
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
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
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