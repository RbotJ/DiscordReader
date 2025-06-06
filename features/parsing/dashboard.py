"""
Parsing Dashboard Module

Web dashboard for viewing and managing parsed trade setups.
"""
import logging
from datetime import date, datetime
from flask import Blueprint, render_template, request, jsonify

from .service import get_parsing_service
from .store import get_parsing_store

logger = logging.getLogger(__name__)

# Create blueprint for parsing dashboard
parsing_dashboard_bp = Blueprint('parsing_dashboard', __name__, url_prefix='/parsing')

@parsing_dashboard_bp.route('/')
def dashboard():
    """Main parsing dashboard"""
    return render_template('parsing/dashboard.html')

@parsing_dashboard_bp.route('/setups')
def setups_view():
    """View parsed setups"""
    trading_day_str = request.args.get('trading_day')
    ticker = request.args.get('ticker')
    
    # Parse trading day
    trading_day = None
    if trading_day_str:
        try:
            trading_day = datetime.strptime(trading_day_str, '%Y-%m-%d').date()
        except ValueError:
            trading_day = date.today()
    
    service = get_parsing_service()
    setups = service.get_active_setups(trading_day, ticker)
    
    return render_template('parsing/setups.html', 
                         setups=setups, 
                         trading_day=trading_day or date.today(),
                         ticker=ticker)

@parsing_dashboard_bp.route('/stats')
def stats_view():
    """View parsing statistics"""
    service = get_parsing_service()
    stats = service.get_service_stats()
    
    return render_template('parsing/stats.html', stats=stats)

def register_dashboard_routes(app):
    """Register parsing dashboard routes"""
    app.register_blueprint(parsing_dashboard_bp)