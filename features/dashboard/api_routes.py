"""
Dashboard API Routes

This module provides API endpoints for the dashboard feature.
"""

from flask import jsonify, request
from . import dashboard_bp
from .services.data_service import (
    get_dashboard_summary,
    get_discord_stats,
    get_trade_monitor_data,
    get_setup_data,
    get_daily_performance,
    get_status_summary
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
def status_summary():
    """Get comprehensive status summary including Discord messages and parsed setups."""
    try:
        data = get_status_summary()
        return jsonify(data)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@dashboard_bp.route('/status-page', methods=['GET'])
def status_page():
    """Render the status dashboard page."""
    from flask import render_template
    return render_template('dashboard/status.html')

def register_routes(app):
    """Register dashboard routes with the Flask app."""
    app.register_blueprint(dashboard_bp)
    return app