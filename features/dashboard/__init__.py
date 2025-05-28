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
    """Basic status route that redirects to enhanced dashboard."""
    from flask import redirect, url_for
    return redirect(url_for('dashboard_api.get_enhanced_status'))

# Version information
__version__ = '0.1.0'