"""
Dashboard Feature

This module provides a unified dashboard system for the A+ Trading application.
"""

from flask import Blueprint

# Create a Blueprint for the dashboard feature
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

# Import routes to register them with the Blueprint
from . import api_routes

# Version information
__version__ = '0.1.0'