"""
Dashboard Feature

This module provides a unified dashboard system for the A+ Trading application.
"""

from flask import Blueprint

# Create a Blueprint for the dashboard feature
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

# Import routes to register them with the Blueprint
from . import api_routes

# Add basic status route
@dashboard_bp.route('/status')
def status():
    """Main status dashboard with HTML interface."""
    from flask import render_template
    from .services.data_service import get_system_status
    
    try:
        # Get system status data
        status_data = get_system_status()
        
        # Render the HTML template with the data
        return render_template('dashboard/status.html', **status_data)
        
    except Exception as e:
        # Render template with error state
        return render_template('dashboard/status.html', 
                             error=str(e),
                             recent_discord_messages=[],
                             todays_messages_count=0,
                             todays_setups=[],
                             tickers_summary=[])

# Version information
__version__ = '0.1.0'