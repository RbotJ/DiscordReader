"""
API routes for market data integration.

This module provides API endpoints for interacting with market data,
managing the watchlist, and retrieving price information.
"""
import logging
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import dateutil.parser

from features.market.client import (
    initialize_clients,
    get_tradable_assets,
    get_latest_bars,
    get_latest_quotes,
    get_historical_bars,
    add_symbols_to_watchlist,
    remove_symbols_from_watchlist,
    get_watchlist,
    start_stream,
    stop_stream
)

# Configure logger
logger = logging.getLogger(__name__)

# Create Blueprint
market_routes = Blueprint('market', __name__)

# Initialize clients on startup
initialize_clients()

@market_routes.route('/api/market/status', methods=['GET'])
def market_status():
    """Get current market status."""
    # This is a simple endpoint to check if the market API is working
    status = initialize_clients()
    return jsonify({
        "status": "ok" if status else "error",
        "message": "Alpaca clients initialized successfully" if status else "Failed to initialize Alpaca clients"
    })

@market_routes.route('/api/market/assets', methods=['GET'])
def get_assets():
    """Get list of tradable assets."""
    asset_type = request.args.get('type', 'us_equity')
    status = request.args.get('status', 'active')
    assets = get_tradable_assets(asset_type, status)
    return jsonify(assets)

@market_routes.route('/api/market/search', methods=['GET'])
def search_symbols():
    """Search for symbols by name or symbol."""
    query = request.args.get('q', '').upper()
    if not query or len(query) < 2:
        return jsonify([])
    
    # Get all assets and filter by query
    assets = get_tradable_assets()
    results = []
    
    for asset in assets:
        symbol = asset.get('symbol', '').upper()
        name = asset.get('name', '').upper()
        
        if query in symbol or query in name:
            results.append(asset)
            
            # Limit to top 20 results
            if len(results) >= 20:
                break
    
    return jsonify(results)

@market_routes.route('/api/market/quotes', methods=['GET'])
def get_quotes():
    """Get latest quotes for symbols."""
    symbols_param = request.args.get('symbols', '')
    symbols = [s.strip().upper() for s in symbols_param.split(',') if s.strip()]
    
    if not symbols:
        return jsonify({"error": "No symbols provided"}), 400
    
    quotes = get_latest_quotes(symbols)
    return jsonify(quotes)

@market_routes.route('/api/market/bars', methods=['GET'])
def get_bars():
    """Get latest bars for symbols."""
    symbols_param = request.args.get('symbols', '')
    symbols = [s.strip().upper() for s in symbols_param.split(',') if s.strip()]
    
    if not symbols:
        return jsonify({"error": "No symbols provided"}), 400
    
    bars = get_latest_bars(symbols)
    return jsonify(bars)

@market_routes.route('/api/market/history', methods=['GET'])
def get_history():
    """Get historical bars for a symbol."""
    symbol = request.args.get('symbol', '').upper()
    timeframe = request.args.get('timeframe', 'day')
    limit = int(request.args.get('limit', 100))
    
    # Parse start/end dates if provided
    start = None
    if 'start' in request.args:
        try:
            start = dateutil.parser.parse(request.args.get('start'))
        except:
            pass
    
    end = None
    if 'end' in request.args:
        try:
            end = dateutil.parser.parse(request.args.get('end'))
        except:
            pass
    
    if not symbol:
        return jsonify({"error": "Symbol is required"}), 400
    
    bars = get_historical_bars(symbol, timeframe, start, end, limit)
    return jsonify(bars)

@market_routes.route('/api/watchlist', methods=['GET'])
def get_watchlist_route():
    """Get the current watchlist."""
    watchlist = get_watchlist()
    return jsonify(watchlist)

@market_routes.route('/api/watchlist', methods=['POST'])
def add_to_watchlist():
    """Add symbols to the watchlist."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    symbols = data.get('symbols', [])
    
    if not symbols:
        return jsonify({"error": "No symbols provided"}), 400
    
    if isinstance(symbols, str):
        symbols = [symbols]
    
    added = add_symbols_to_watchlist(symbols)
    
    # Start the streaming service if items were added
    if added > 0:
        start_stream()
    
    return jsonify({
        "success": True,
        "added": added,
        "symbols": symbols
    })

@market_routes.route('/api/watchlist', methods=['DELETE'])
def remove_from_watchlist():
    """Remove symbols from the watchlist."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    symbols = data.get('symbols', [])
    
    if not symbols:
        return jsonify({"error": "No symbols provided"}), 400
    
    if isinstance(symbols, str):
        symbols = [symbols]
    
    removed = remove_symbols_from_watchlist(symbols)
    
    return jsonify({
        "success": True,
        "removed": removed,
        "symbols": symbols
    })

@market_routes.route('/api/stream', methods=['POST'])
def stream_control():
    """Start or stop the market data stream."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    action = data.get('action', '').lower()
    
    if action == 'start':
        start_stream()
        return jsonify({
            "success": True,
            "status": "started"
        })
    elif action == 'stop':
        stop_stream()
        return jsonify({
            "success": True,
            "status": "stopped"
        })
    else:
        return jsonify({
            "error": "Invalid action, must be 'start' or 'stop'"
        }), 400