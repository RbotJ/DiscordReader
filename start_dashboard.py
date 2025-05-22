
"""
Launch the unified A+ Trading Dashboard

This script starts the consolidated dashboard application with proper configuration.
"""

import os
import sys
import streamlit.web.cli as stcli

def main():
    # Get the path to the main streamlit app
    dashboard_path = os.path.join(os.path.dirname(__file__), "streamlit_app.py")
    
    if not os.path.exists(dashboard_path):
        print(f"Error: Dashboard file not found at {dashboard_path}")
        sys.exit(1)
    
    # Launch the dashboard using Streamlit CLI
    sys.argv = ["streamlit", "run", dashboard_path, 
                "--server.port=8501",
                "--server.address=0.0.0.0"]
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()
