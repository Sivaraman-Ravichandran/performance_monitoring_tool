from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bcrypt import hashpw, gensalt, checkpw

app = Flask(__name__)
CORS(app)

# MongoDB setup
client = MongoClient('mongodb+srv://lmkkrishna110:algo@cluster0.d7axi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client['Authentication']
users_collection = db['Employee']

# Registration endpoint (for HR to create other users)
@app.route('/api/create_user', methods=['POST'])
def create_user():
    data = request.json
    email = data['email']
    password = data['password']
    role = data['role']
    hr_email = data['hr_email']

    # Check if the HR exists and is authorized
    hr_user = users_collection.find_one({'email': hr_email, 'role': 'hr'})
    if not hr_user:
        return jsonify({'success': False, 'message': 'Unauthorized access'}), 403

    # Check if user already exists
    if users_collection.find_one({'email': email}):
        return jsonify({'success': False, 'message': 'User already exists'}), 400

    # Hash the password
    hashed_password = hashpw(password.encode('utf-8'), gensalt())

    # Insert the new user into the database
    users_collection.insert_one({
        'email': email,
        'password': hashed_password,
        'role': role
    })

    return jsonify({'success': True, 'message': 'User created successfully'}), 201

# Login endpoint
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data['email']
    password = data['password']

    user = users_collection.find_one({'email': email})

    if user and checkpw(password.encode('utf-8'), user['password']):
        # Return the dashboard URL based on the user's role
        if user['role'] == 'employee':
            dashboard_url = '/employee/dashboard'
        elif user['role'] == 'team_manager':
            dashboard_url = '/team_manager/dashboard'
        elif user['role'] == 'hr':
            dashboard_url = '/hr/dashboard'
        else:
            return jsonify({'success': False, 'message': 'Unknown role'}), 403

        return jsonify({'success': True, 'message': 'Login successful', 'dashboard_url': dashboard_url}), 200
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

if __name__ == '__main__':
    app.run(debug=True)
