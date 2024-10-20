from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS
import datetime
from flask_socketio import SocketIO, emit  # Import SocketIO

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
socketio = SocketIO(app, cors_allowed_origins="*")  # Initialize SocketIO

# Initialize variables to store time spent on professional and non-professional tabs
professional_time = 0
non_professional_time = 0

# List of professional keywords (you can customize this)
professional_keywords = [
    'github', 'gitlab', 'bitbucket', 'geeksforgeeks', 'stackoverflow', 'w3schools', 
    'mdn', 'codepen', 'leetcode', 'hackerrank', 'kaggle', 'towardsdatascience', 
    'linkedin', 'slack', 'teams', 'zoom', 'google meet', 'trello', 'jira', 'confluence', 
    'salesforce', 'datadog', 'aws', 'azure', 'google cloud', 'docker', 'jenkins', 
    'devops', 'chatgpt', 'figma', 'canva', 'microsoft 365', 'notion'
]

@app.route('/log-tab-data', methods=['POST'])
def log_tab_data():
    global professional_time, non_professional_time

    # Get the title and time spent from the request data
    data = request.get_json()
    title = data.get('title')
    time_spent = data.get('timeSpent', 0)

    # Check if the tab title contains any professional keywords
    if any(keyword in title.lower() for keyword in professional_keywords):
        professional_time += time_spent
        category = 'Professional'
    else:
        non_professional_time += time_spent
        category = 'Non-Professional'

    # Print the data and time spent in both categories
    print(f"Tab Title: {title}, Time Spent: {time_spent}s, Category: {category}")
    print(f"Total Professional Time: {professional_time}s, Non-Professional Time: {non_professional_time}s")

    # Emit updated time data to all connected clients
    socketio.emit('time_update', {
        'professional_time': professional_time,
        'non_professional_time': non_professional_time
    })

    return jsonify({'message': 'Data received successfully'})


if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=5001, debug=True)
