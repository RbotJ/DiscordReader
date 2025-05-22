"""
Dashboard Main Application

This is the main entry point for the unified dashboard application.
It provides access to all dashboard views through a streamlined navigation system.
"""

import os
import streamlit as st
import logging
from datetime import datetime
from importlib import import_module

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Streamlit page
st.set_page_config(
    page_title="A+ Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Define available views
AVAILABLE_VIEWS = {
    "main": {
        "name": "Main Dashboard",
        "description": "Overview of account status, positions, and performance",
        "module": "features.dashboard.views.main_view"
    },
    "discord": {
        "name": "Discord Stats",
        "description": "Statistics about Discord messages and trading setups",
        "module": "features.dashboard.views.discord_view"
    },
    "trades": {
        "name": "Trade Monitor",
        "description": "Real-time monitoring of active trades",
        "module": "features.dashboard.views.trade_view"
    },
    "setups": {
        "name": "Setup Monitor",
        "description": "Tracking of trade setups and market signals",
        "module": "features.dashboard.views.setup_view"
    },
    "daily": {
        "name": "Daily Performance",
        "description": "Analysis of daily ticker performance",
        "module": "features.dashboard.views.daily_view"
    }
}

def main():
    """Main application entry point."""
    # Display app header
    st.sidebar.title("A+ Trading Dashboard")
    st.sidebar.image("static/logo.svg", width=100)
    
    # Navigation
    st.sidebar.subheader("Navigation")
    selected_view = st.sidebar.selectbox(
        "Select View",
        options=list(AVAILABLE_VIEWS.keys()),
        format_func=lambda x: AVAILABLE_VIEWS[x]["name"]
    )
    
    # Display view description
    st.sidebar.markdown(AVAILABLE_VIEWS[selected_view]["description"])
    
    # Last updated timestamp
    st.sidebar.markdown("---")
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.sidebar.markdown(f"Last updated: {current_time}")
    
    # Display the selected view
    st.title(AVAILABLE_VIEWS[selected_view]["name"])
    
    try:
        # Dynamic import of the selected view module
        view_module = import_module(AVAILABLE_VIEWS[selected_view]["module"])
        
        # Render the view
        view_module.render()
    except ImportError as e:
        st.error(f"Could not load view '{selected_view}': {e}")
        st.info("This view may not be implemented yet. Please check back later.")
    except Exception as e:
        st.error(f"Error rendering view '{selected_view}': {e}")
        logger.exception(f"Error rendering view '{selected_view}'")
        
        # Fallback view
        st.markdown("## Dashboard View Currently Unavailable")
        st.markdown("We're experiencing technical difficulties loading this view. Please try another view or check back later.")

if __name__ == "__main__":
    main()