from services.jwt_config import jwt, configure_jwt
from flask import Flask, request, jsonify
from flask_cors import CORS
from models import db
from config import config
from routes import api
import redis


# Initialize Flask app
app = Flask(__name__, static_url_path='/static', static_folder='static')
app.config.from_object(config)


# Register API Blueprint
app.register_blueprint(api)


# Initialize CORS
CORS(app, resources={r"/api/*": {"origins": "*"}}, 
     supports_credentials=True, 
     allow_headers=["Content-Type", "Authorization"])

db.init_app(app)
configure_jwt(app)



# create tables (run this separately)
def init_db():
    with app.app_context():
        db.create_all()
        print("Database tables created!")


@app.route('/')
def Home():
    return f"Welcome to our Site {config.JWT_SECRET_KEY}"

if __name__ == '__main__': 

    init_db()
    app.run(debug=True, port=8057, host='0.0.0.0')


