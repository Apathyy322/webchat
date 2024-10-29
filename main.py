import sqlite3
from flask import Flask, request, render_template
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'pusiclat'
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

# Ensure the templates directory exists
if not os.path.exists('templates'):
    os.makedirs('templates')

def init_db():
    conn = sqlite3.connect('chat_users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE)''')
    conn.commit()
    conn.close()

def add_user(username):
    try:
        conn = sqlite3.connect('chat_users.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (username) VALUES (?)", (username,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    try:
        username = request.json.get('username')
        if not username:
            return "Username is required", 400
        
        if add_user(username):
            return "User registered successfully", 200
        else:
            return "Username already exists", 400
    except Exception as e:
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
    init_db()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
