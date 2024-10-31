import os
import logging
from flask import Flask, request, render_template
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///chat_users.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Log configuration details (excluding sensitive info)
logger.info(f"Starting app with DATABASE_URL configured: {'Yes' if 'DATABASE_URL' in os.environ else 'No'}")
logger.info(f"Running in {'development' if app.debug else 'production'} mode")

CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

# Initialize database tables
def init_db():
    with app.app_context():
        logger.info("Creating database tables...")
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise

# Initialize the database tables
init_db()

@app.route('/')
def home():
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering home page: {e}")
        return "Internal Server Error", 500

@app.route('/register', methods=['POST'])
def register():
    try:
        username = request.json.get('username')
        if not username:
            logger.warning("Registration attempted with empty username")
            return "Username is required", 400
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            logger.info(f"Registration attempted with existing username: {username}")
            return "Username already exists", 400
            
        new_user = User(username=username)
        db.session.add(new_user)
        db.session.commit()
        logger.info(f"New user registered: {username}")
        return "User registered successfully", 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during registration: {e}")
        return "Registration failed", 500

@socketio.on('chat message')
def handle_message(data):
    try:
        username = data.get('username')
        message = data.get('message')
        if username and message:
            logger.info(f"Received message from {username}")
            emit('chat message', {
                'username': username,
                'message': message
            }, broadcast=True)
        else:
            logger.warning("Received incomplete message data")
    except Exception as e:
        logger.error(f"Error handling message: {e}")

@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal Server Error: {error}")
    return "Internal Server Error", 500

@app.errorhandler(404)
def not_found_error(error):
    logger.error(f"Page not found: {error}")
    return "Page Not Found", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
