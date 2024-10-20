from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bcrypt import hashpw, gensalt, checkpw
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string
from datetime import datetime
from bson import ObjectId
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import pandas as pd
import numpy as np
import csv

app = Flask(__name__)
CORS(app)

# MongoDB setup
client = MongoClient('mongodb+srv://lmkkrishna110:algo@cluster0.d7axi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client['Authentication']
users_collection = db['Employee']
session_collection = db['Session']
team_manager_collection = db['TeamManager_details'] 
employee_collection = db['Employee_detail']

# Load CSV file and prepare the model (same logic as before)
csv_file = 'Employee_Performance.csv'
data = pd.read_csv(csv_file)

# Encode categorical data
label_encoders = {}
for column in data.columns:
    if data[column].dtype == 'object':
        le = LabelEncoder()
        data[column] = le.fit_transform(data[column])
        label_encoders[column] = le

# Split dataset for feedback prediction
X = data.drop(columns=['Feedback'])
y_feedback = data['Feedback']

# Train/Test split
X_train, X_test, y_feed_train, y_feed_test = train_test_split(X, y_feedback, test_size=0.2, random_state=42)

# Train RandomForest model for feedback
feedback_model = RandomForestClassifier()
feedback_model.fit(X_train, y_feed_train)
# Registration endpoint (for HR to create other users)
@app.route('/api/create_user', methods=['POST'])
def create_user():
    data = request.json
    email = data['email']
    password = data['password']
    role = data['role']
    
    # Check if user already exists
    if users_collection.find_one({'email': email}):
        return jsonify({'success': False, 'message': 'User already exists'}), 400

    # Hash the password
    hashed_password = hashpw(password.encode('utf-8'), gensalt()).decode('utf-8')  # Store as string

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

    if user and checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):  # Convert stored password to bytes
        # Return the dashboard URL based on the user's role
        if user['role'] == 'employee':
            dashboard_url = '/employee/dashboard'
        elif user['role'] == 'team_manager':
            dashboard_url = '/team_manager/dashboard'
        elif user['role'] == 'hr':
            dashboard_url = '/hr/dashboard'
        else:
            return jsonify({'success': False, 'message': 'Unknown role'}), 403

        return jsonify({
            'success': True,
            'message': 'Login successful',
            'dashboard_url': dashboard_url,
            'employee_id': str(user['_id'])  # Return the employee ID as a string
        }), 200
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/api/create_session', methods=['POST'])
def create_session():
    data = request.json
    employee_id = data['employee_id']

    # Get the current time as start time
    in_date_time = datetime.now()  # Current time in UTC

    # Create a new session document with an auto-generated ID
    session_document = {
        "employee_id": employee_id,  # Store the employee ID
        "inDateTime": in_date_time,
        "outDateTime": None,  # Initially set to None
        "totalWorkingHours": 0,  # Initially set to 0
        "totalIdleTime": 0 , # Initialize idle time if needed
        "task_completion_rate":0.3,
        "goals_achieved":3
    }

    # Insert the session document into the database
    result = session_collection.insert_one(session_document)
    
    # Use the inserted ID as the session ID
    session_id = str(result.inserted_id)  # Get the auto-generated session ID

    return jsonify({'success': True, 'session_id': session_id, 'inDateTime': in_date_time}), 201

# Utility function to calculate total working hours
def calculate_working_hours(start_time, end_time):
    total_hours = (end_time - start_time).total_seconds() / 3600  # Convert seconds to hours
    return round(total_hours, 2)  # Return rounded value for working hours

@app.route('/api/end_session', methods=['POST'])
def end_session():
    data = request.json
    session_id = data['session_id'].strip()  # Remove leading/trailing spaces

    # Debugging: Log the session_id received
    print(f"Received session_id: {session_id} (type: {type(session_id)})")

    # Check if the session_id is a valid length for ObjectId
    if len(session_id) != 24:
        return jsonify({'success': False, 'message': 'Invalid session ID format'}), 400

    # Convert session_id to ObjectId
    try:
        session_id = ObjectId(session_id)
    except Exception as e:
        print(f"Error converting session_id to ObjectId: {e}")  # Log the error
        return jsonify({'success': False, 'message': 'Invalid session ID format'}), 400

    # Fetch the session for the given session_id
    session = session_collection.find_one({'_id': session_id})

    if session:
        start_time = session.get('inDateTime')  # Ensure 'inDateTime' exists

        # Ensure start_time is a datetime object, convert if necessary
        if isinstance(start_time, str):
            try:
                start_time = datetime.fromisoformat(start_time.replace('Z', ''))
            except Exception as e:
                print(f"Error parsing start_time: {e}")
                return jsonify({'success': False, 'message': 'Error parsing start_time'}), 400

        # Get the current time
        current_time = datetime.now()

        # Debugging: Log start_time and current_time
        print(f"Start Time: {start_time}, Current Time: {current_time}")

        # Calculate total working hours (difference between start_time and current_time)
        total_working_hours = calculate_working_hours(start_time, current_time)

        # Debugging: Log total working hours
        print(f"Total Working Hours: {total_working_hours}")

        # Update the session with outDateTime and totalWorkingHours
        session_collection.update_one(
            {'_id': session_id},
            {
                '$set': {
                    'outDateTime': current_time.isoformat(),  # Store in ISO format
                    'totalWorkingHours': total_working_hours
                }
            }
        )

        # Optional: Fetch the updated session data for confirmation
        updated_session = session_collection.find_one({'_id': session_id})
        print(f"Updated session data: {updated_session}")  # Log updated session data for debugging

        return jsonify({'success': True, 'message': 'Session updated successfully'}), 200
    else:
        return jsonify({'success': False, 'message': 'Session not found for this session ID'}), 404


@app.route('/api/update_idle_time', methods=['POST'])
def update_idle_time():
    data = request.json
    session_id = data['session_id']  # Use session_id as the identifier
    new_idle_time = data['idle_time']  # Idle time in seconds

    # Debugging: Log the session ID received
    print(f"Received session_id: {session_id}")

    # Convert session_id to ObjectId
    try:
        session_id = ObjectId(session_id)
    except Exception as e:
        print(f"Error converting session_id to ObjectId: {e}")  # Log the error
        return jsonify({'success': False, 'message': 'Invalid session ID format'}), 400

    # Fetch the session for the given session_id
    session = session_collection.find_one({'_id': session_id})
    print(session)
    if session:
        # Get current total idle time from the session, or initialize to 0 if not present
        previous_idle_time = session.get('totalIdleTime', 0)  # Default to 0 for older records

        # Add the new idle time to the previous total
        updated_idle_time = previous_idle_time + new_idle_time
        print(update_idle_time)
        # Update the session with the new total idle time
        session_collection.update_one(
            {'_id': session_id},
            {
                '$set': {
                    'totalIdleTime': 40  # Create the field if it does not exist
                }
            }
        )

        return jsonify({'success': True, 'message': 'Idle time updated successfully'}), 200
    else:
        return jsonify({'success': False, 'message': 'Session not found for this session ID'}), 404
    
@app.route('/api/analysis/<employee_id>', methods=['GET'])
def analysis(employee_id):
    # Fetch session data for the given employee_id
    session = session_collection.find_one({'employee_id': employee_id})

    if not session:
        return jsonify({'success': False, 'message': 'Session data not found for the employee.'}), 404

    # Extract real-time employee data from the session
    task_completion_rate = session.get('task_completion_rate', 0)
    working_hours = session.get('totalWorkingHours', 0)
    idle_time = session.get('totalIdleTime', 0)
    goals_achieved = session.get('goals_achieved', 0)

    # Prepare real-time data for prediction
    real_time_data = pd.DataFrame({
        'TaskCompletionRate': [task_completion_rate],
        'WorkingHours': [working_hours],
        'IdleTime': [idle_time],
        'GoalsAchieved': [goals_achieved]
    })

    # Predict feedback using the trained model
    predicted_feedback = feedback_model.predict(real_time_data)

    # Convert the predicted_feedback to a Python int if it's in a non-serializable format
    if isinstance(predicted_feedback[0], (np.int64, np.float64)):  # Handle NumPy data types
        predicted_feedback_value = int(predicted_feedback[0])
    else:
        predicted_feedback_value = predicted_feedback[0]

    # Custom feedback based on real-time data
    custom_feedback = ''
    
    # TaskCompletionRate-based feedback
    if task_completion_rate >= 0.8:
        custom_feedback = "Excellent task completion rate! Keep up the consistency."
    elif task_completion_rate >= 0.6:
        custom_feedback = "Good job, but there's room to improve your task completion rate."
    else:
        custom_feedback = "You need to focus more on completing tasks efficiently."
    
    # WorkingHours-based feedback
    if working_hours >= 8:
        custom_feedback += " You're working full hours, well done!"
    elif working_hours >= 6:
        custom_feedback += " You're working a decent amount, but try to avoid distractions."
    else:
        custom_feedback += " Consider putting in more working hours to meet your goals."
    
    # IdleTime-based feedback
    if idle_time <= 0.5:
        custom_feedback += " Your idle time is minimal, great focus!"
    elif idle_time <= 1.5:
        custom_feedback += " Try reducing your idle time to improve productivity."
    else:
        custom_feedback += " Your idle time is quite high, focus on staying active."
    
    # GoalsAchieved-based feedback
    if goals_achieved >= 5:
        custom_feedback += " You've achieved all your goals, amazing work!"
    elif goals_achieved >= 3:
        custom_feedback += " You've met some of your goals, but aim for more next time."
    else:
        custom_feedback += " You need to work harder to achieve your goals."

    # Convert new_data into a DataFrame with the feedback enclosed in double quotes
    data_df = pd.DataFrame([[
        task_completion_rate,
        working_hours,
        idle_time,
        goals_achieved,
        f'"{custom_feedback}"'  # Add custom feedback as a column
    ]], columns=['TaskCompletionRate', 'WorkingHours', 'IdleTime', 'GoalsAchieved', 'Feedback'])

    # Append new data to the CSV file
    data_df.to_csv('Employee_Performance.csv', mode='a', header=False, index=False, quoting=csv.QUOTE_NONNUMERIC)


    # Return final feedback as response
    return jsonify({
        'success': True,
        'predicted_feedback': predicted_feedback_value,  # Use the converted Python int
        'custom_feedback': custom_feedback
    }), 200

@app.route('/api/employee_data/<employee_id>', methods=['GET'])
def get_employee_data(employee_id):
    # Fetch employee data based on employee_id
    employee_data = session_collection.find_one({'employee_id': employee_id})

    if not employee_data:
        return jsonify({'success': False, 'message': 'Employee not found.'}), 404

    # Extract relevant fields
    result = {
        'inDateTime': employee_data.get('inDateTime', None),
        'outDateTime': employee_data.get('outDateTime', None),
        'task_completion_rate': employee_data.get('task_completion_rate', None),
        'goals_achieved': employee_data.get('goals_achieved', None),
        'total_idle_time': employee_data.get('totalIdleTime', None),
        'total_working_hours': employee_data.get('totalWorkingHours', None),
    }

    return jsonify({'success': True, 'data': result}), 200  # Ensure a 200 status code
# Update user profile route
@app.route('/update-profile/<user_id>', methods=['PUT'])
def update_profile(user_id):
    try:
        # Get the JSON data from the request
        data = request.json
        
        # Extract the updated fields
        name = data.get('name')
        phone = data.get('phone')
        email = data.get('email')
        password = data.get('password')
        dob = data.get('dob')  # Date of birth
        
        # Find the user by ID in the MongoDB collection
        user = db.users.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        # Create an update dictionary
        update_fields = {}
        
        if name:
            update_fields['name'] = name
        if phone:
            update_fields['phone'] = phone
        if email:
            update_fields['email'] = email
        if password:
            hashed_password = generate_password_hash(password)
            update_fields['password'] = hashed_password
        if dob:
            update_fields['dob'] = dob
        
        # Update the user profile in the database
        if update_fields:
            db.users.update_one({'_id': ObjectId(user_id)}, {'$set': update_fields})
            return jsonify({'message': 'Profile updated successfully'}), 200
        else:
            return jsonify({'message': 'No fields to update'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/get-profile/<user_id>', methods=['GET'])
def get_profile(user_id):
    try:
        # Find the user in the MongoDB collection by their ObjectId
        user = db.users.find_one({'_id': ObjectId(user_id)})
        
        if not user:
            return jsonify({'message': 'User not found'}), 404

        # Prepare the user profile to send as response (excluding sensitive fields)
        user_profile = {
            'name': user.get('name'),
            'phone': user.get('phone'),
            'email': user.get('email'),
            'dob': user.get('dob')  # Date of birth
        }

        return jsonify(user_profile), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/employee_performance/<employee_id>', methods=['GET'])
def get_employee_performance(employee_id):
    try:
        # Convert the string employee_id to ObjectId
        employee = employee_collection.find_one({"_id": ObjectId(employee_id)})

        if not employee:
            return jsonify({"success": False, "message": "Employee not found."}), 404

        # Return the employee performance metrics
        performance_metrics = employee.get("performance_metrics", {})
        return jsonify({"success": True, "performance_metrics": performance_metrics}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
@app.route('/api/employee_performance', methods=['GET'])
def get_all_employees():
    try:
        # Retrieve all employees from the Employee_Detail collection
        employees = employee_collection.find()

        # Convert the cursor into a list and ensure proper JSON serialization
        employees_list = []
        for employee in employees:
            # Convert ObjectId to string for JSON serialization
            employee['_id'] = str(employee['_id'])
            employee['team_manager_id'] = str(employee['team_manager_id'])
            
            # Convert any other nested ObjectId fields to string if necessary
            for feedback in employee.get('feedbacks', []):
                feedback['manager_id'] = str(feedback['manager_id'])

            employees_list.append(employee)

        return jsonify({"success": True, "employees": employees_list}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
   
if __name__ == '__main__':
    app.run(debug=True)