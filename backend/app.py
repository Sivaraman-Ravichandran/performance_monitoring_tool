from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bcrypt import hashpw, gensalt, checkpw
import re  # For password validation

app = Flask(__name__)
CORS(app)

# MongoDB setup
client = MongoClient('mongodb+srv://lmkkrishna110:algo@cluster0.d7axi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client['Authentication']
users_collection = db['Employee']

# Password validation function
def validate_password(password):
    """
    Validates the password based on the following criteria:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit
    - Contains at least one special character
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one digit."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character."
    return True, ""

# Endpoint for HR to create other users (employees, team managers, etc.)
@app.route('/api/create_user', methods=['POST'])
def create_user():
    data = request.json
    email = data['email']
    password = data['password']
    role = data['role']

    # Check if the user already exists
    if users_collection.find_one({'email': email}):
        return jsonify({'success': False, 'message': 'User already exists'}), 400

    # Validate password
    is_valid, message = validate_password(password)
    if not is_valid:
        return jsonify({'success': False, 'message': message}), 400

    # Hash the password and convert to string for storage
    hashed_password = hashpw(password.encode('utf-8'), gensalt()).decode('utf-8')

    # Insert the new user into the database
    users_collection.insert_one({
        'email': email,
        'password': hashed_password,
        'role': role  # 'employee', 'team_manager', 'hr', or 'system_admin'
    })

    return jsonify({'success': True, 'message': 'User created successfully'}), 201

# Login endpoint
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data['email']
    password = data['password']

    # Find user by email
    user = users_collection.find_one({'email': email})

    if user and checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        # Determine the appropriate dashboard based on the user's role
        if user['role'] == 'employee':
            dashboard_url = '/employee/dashboard'
        elif user['role'] == 'team_manager':
            dashboard_url = '/team_manager/dashboard'
        elif user['role'] == 'hr':
            dashboard_url = '/hr/dashboard'
        elif user['role'] == 'system_admin':
            dashboard_url = '/system_admin/dashboard'
        else:
            return jsonify({'success': False, 'message': 'Unknown role'}), 403

        return jsonify({'success': True, 'message': 'Login successful', 'dashboard_url': dashboard_url}), 200
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

# Start the Flask application
if __name__ == '__main__':
    app.run(debug=True)
