#!/bin/bash
# Start the Streamlit dashboard that connects to the Flask backend

echo "Starting Flask-connected Streamlit Trading Dashboard..."

# Run on port 8501 to avoid conflict with Flask (port 5000)
streamlit run flask_streamlit_dashboard.py --server.port=8501