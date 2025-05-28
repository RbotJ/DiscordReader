"""
Dashboard API Routes

This module provides API endpoints for the dashboard feature.
"""

from flask import jsonify, request, render_template
from . import dashboard_bp
from .services.data_service import (
    get_dashboard_summary,
    get_discord_stats,
    get_trade_monitor_data,
    get_setup_data,
    get_daily_performance,
    get_system_status
)

# Register routes with the dashboard blueprint
@dashboard_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for dashboard API."""
    return jsonify({
        'status': 'ok',
        'feature': 'dashboard',
        'version': '0.1.0'
    })

@dashboard_bp.route('/data/summary', methods=['GET'])
def get_data_summary():
    """Get summary data for the main dashboard."""
    try:
        summary = get_dashboard_summary()
        return jsonify(summary)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@dashboard_bp.route('/data/discord-stats', methods=['GET'])
def get_discord_stats_route():
    """Get Discord message statistics."""
    try:
        stats = get_discord_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@dashboard_bp.route('/data/trade-monitor', methods=['GET'])
def get_trade_monitor_data_route():
    """Get data for trade monitoring."""
    try:
        data = get_trade_monitor_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@dashboard_bp.route('/data/setups', methods=['GET'])
def get_setup_data_route():
    """Get data for setup monitoring."""
    try:
        data = get_setup_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@dashboard_bp.route('/data/daily-performance', methods=['GET'])
def get_daily_performance_route():
    """Get daily ticker performance data."""
    try:
        date_str = request.args.get('date')
        data = get_daily_performance(date_str)
        return jsonify(data)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@dashboard_bp.route('/status', methods=['GET'])
def system_status():
    """Get system status showing operational telemetry."""
    try:
        # Get system status data
        status_data = get_system_status()
        
        # Check if JSON format is requested
        format_requested = request.args.get('format', '').lower()
        if format_requested == 'json':
            return jsonify(status_data)
        
        # Otherwise, render HTML template
        return render_template('dashboard/status.html', **status_data)
        
    except Exception as e:
        error_data = {
            'status': 'error',
            'message': str(e),
            'recent_discord_messages': [],
            'todays_messages_count': 0,
            'todays_setups': [],
            'tickers_summary': [],
            'error': str(e)
        }
        
        # Return JSON error if requested, otherwise render error template
        format_requested = request.args.get('format', '').lower()
        if format_requested == 'json':
            return jsonify(error_data), 500
        
        return render_template('dashboard/status.html', **error_data), 500

def register_routes(app):
    """Register dashboard routes with the Flask app."""
    app.register_blueprint(dashboard_bp)
    return app