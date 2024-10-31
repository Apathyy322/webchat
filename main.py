import os
from flask import Flask, request, render_template
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///chat_users.db')
# Handle Heroku postgres:// vs postgresql:// issue
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Update CORS to allow your GitHub Pages domain
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

@app.before_first_request
def create_tables():
    db.create_all()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    try:
        username = request.json.get('username')
        if not username:
            return "Username is required", 400
        
        if User.query.filter_by(username=username).first():
            return "Username already exists", 400
            
        new_user = User(username=username)
        db.session.add(new_user)
        db.session.commit()
        return "User registered successfully", 200
    except Exception as e:
        db.session.rollback()
        print(f"Error during registration: {e}")
        return "Registration failed", 500

@socketio.on('chat message')
def handle_message(data):
    try:
        username = data.get('username')
        message = data.get('message')
        if username and message:
            print(f"Received message from {username}: {message}")
            emit('chat message', {
                'username': username,
                'message': message
            }, broadcast=True)
    except Exception as e:
        print(f"Error handling message: {e}")

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
