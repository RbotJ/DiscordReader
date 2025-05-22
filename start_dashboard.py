"""
Launch the unified A+ Trading Dashboard

This script starts the consolidated dashboard application.
"""

import os
import sys
import streamlit.web.cli as stcli
from features.dashboard.app import main

if __name__ == "__main__":
    # Get the path to the app.py file
    dashboard_path = os.path.join(os.path.dirname(__file__), "features", "dashboard", "app.py")
    
    # Check if the file exists
    if not os.path.exists(dashboard_path):
        print(f"Error: Dashboard file not found at {dashboard_path}")
        sys.exit(1)
    
    # Launch the dashboard using Streamlit CLI
    sys.argv = ["streamlit", "run", dashboard_path]
    sys.exit(stcli.main())