"""
Simple Discord Message Dashboard

A simplified version of the dashboard that displays basic information
about Discord messages directly in the browser.
"""
from flask import Flask, render_template_string
import json
import os
from datetime import datetime

app = Flask(__name__)

# Storage file paths
MESSAGE_HISTORY_FILE = "discord_message_history.json"
LATEST_MESSAGE_FILE = "latest_discord_message.json"

def load_message_history():
    """Load the message history from file"""
    if os.path.exists(MESSAGE_HISTORY_FILE):
        try:
            with open(MESSAGE_HISTORY_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            return []
    return []

def load_latest_message():
    """Load the latest message from file"""
    if os.path.exists(LATEST_MESSAGE_FILE):
        try:
            with open(LATEST_MESSAGE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            return None
    return None

def format_timestamp(timestamp_str):
    """Format ISO timestamp to readable date/time"""
    try:
        dt = datetime.fromisoformat(timestamp_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp_str

# HTML template for the dashboard
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Discord Message Stats</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }
        .stats-container {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            flex: 1;
            min-width: 200px;
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        .stat-title {
            font-size: 14px;
            color: #7f8c8d;
            margin-bottom: 5px;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }
        .message-container {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
        }
        .message-header {
            display: flex;
            justify-content: space-between;
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
            margin-bottom: 10px;
        }
        .message-content {
            white-space: pre-wrap;
            background-color: white;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }
        .message-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        .message-table th, .message-table td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .message-table th {
            background-color: #f2f2f2;
        }
        .message-table tr:hover {
            background-color: #f5f5f5;
        }
        .refresh-button {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin-top: 20px;
        }
        .refresh-button:hover {
            background-color: #2980b9;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Discord Message Statistics</h1>
        
        <div class="stats-container">
            <div class="stat-card">
                <div class="stat-title">Total Messages</div>
                <div class="stat-value">{{ message_count }}</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-title">Latest Message Time</div>
                <div class="stat-value">{{ latest_time }}</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-title">Latest Author</div>
                <div class="stat-value">{{ latest_author }}</div>
            </div>
        </div>
        
        {% if latest_message %}
        <h2>Latest Message</h2>
        <div class="message-container">
            <div class="message-header">
                <div><strong>Author:</strong> {{ latest_message.author }}</div>
                <div><strong>Channel:</strong> {{ latest_message.channel_name }}</div>
                <div><strong>Time:</strong> {{ format_time(latest_message.timestamp) }}</div>
            </div>
            <div class="message-content">{{ latest_message.content }}</div>
        </div>
        {% endif %}
        
        {% if message_history %}
        <h2>Message History</h2>
        <table class="message-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Time</th>
                    <th>Author</th>
                    <th>Channel</th>
                </tr>
            </thead>
            <tbody>
                {% for message in message_history %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td>{{ format_time(message.timestamp) }}</td>
                    <td>{{ message.author }}</td>
                    <td>{{ message.channel_name }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}
        
        <button class="refresh-button" onclick="location.reload();">Refresh Data</button>
    </div>
</body>
</html>
"""

@app.route('/')
def discord_dashboard():
    message_history = load_message_history()
    latest_message = load_latest_message()
    
    latest_time = "N/A"
    latest_author = "N/A"
    
    if latest_message and "timestamp" in latest_message:
        latest_time = format_timestamp(latest_message["timestamp"])
    
    if latest_message and "author" in latest_message:
        latest_author = latest_message.get("author", "Unknown")
    
    return render_template_string(
        DASHBOARD_TEMPLATE,
        message_count=len(message_history),
        latest_time=latest_time,
        latest_author=latest_author,
        latest_message=latest_message,
        message_history=message_history,
        format_time=format_timestamp
    )

if __name__ == "__main__":
    # Run the Flask app
    app.run(host="0.0.0.0", port=5001, debug=True)