"""
Market Data API Routes

This module provides API endpoints for market data, including
real-time stock data, historical prices, and market status.
"""
import logging
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta

from features.market.service import get_market_service

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint('market', __name__, url_prefix='/api/market')

@bp.route('/status', methods=['GET'])
def get_market_status():
    """
    Get current market status.
    
    Returns:
        JSON with market open status and next open/close times
    """
    try:
        market_service = get_market_service()
        status = market_service.get_market_status()
        
        if not status:
            return jsonify({
                'status': 'error',
                'message': 'Could not retrieve market status'
            }), 500
        
        return jsonify({
            'status': 'success',
            'market_open': status.is_open,
            'session': status.session,
            'next_open': status.next_open.isoformat() if status.next_open else None,
            'next_close': status.next_close.isoformat() if status.next_close else None
        })
            
        return jsonify({
            'status': 'success',
            'is_open': market_open,
            'next_open': next_open.isoformat() if not market_open else None,
            'next_close': next_close.isoformat() if market_open else None
        })
    except Exception as e:
        logger.error(f"Error getting market status: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Error retrieving market status'
        }), 500

@bp.route('/candles/<symbol>', methods=['GET'])
def get_candles(symbol):
    """
    Get candle data for a symbol.
    
    Query params:
        timeframe: Candle timeframe (default: 5m)
        limit: Maximum number of candles to return (default: 100)
        start: Start date/time for historical data (optional)
        end: End date/time for historical data (optional)
        
    Returns:
        JSON with candle data
    """
    try:
        # Parse query parameters
        timeframe = request.args.get('timeframe', '5m')
        limit = int(request.args.get('limit', 100))
        start = request.args.get('start')
        end = request.args.get('end')
        
        # Get market service and candle data
        market_service = get_market_service()
        candles = market_service.get_candles(symbol, timeframe, start, end, limit)
        
        if not candles:
            return jsonify({
                'status': 'error',
                'message': f'No candle data available for {symbol}'
            }), 404
            
        # Convert CandleData objects to dictionaries
        candles_dict = []
        for candle in candles:
            candles_dict.append({
                'timestamp': candle.timestamp.isoformat(),
                'open': candle.open,
                'high': candle.high,
                'low': candle.low,
                'close': candle.close,
                'volume': candle.volume
            })
            
        return jsonify({
            'status': 'success',
            'symbol': symbol.upper(),
            'timeframe': timeframe,
            'candles': candles_dict
        })
    except Exception as e:
        logger.error(f"Error getting candles for {symbol}: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving candle data for {symbol}'
        }), 500

@bp.route('/quote/<symbol>', methods=['GET'])
def get_quote(symbol):
    """
    Get the latest quote for a symbol.
    
    Returns:
        JSON with quote data
    """
    try:
        # Get real-time data service
        market_feed = get_market_feed()
        
        # Get last quote from feed
        quote = market_feed.get_last_quote(symbol)
        
        if not quote:
            # Fallback to Alpaca API if we don't have a cached quote
            from features.alpaca.client import get_latest_quote
            quote = get_latest_quote(symbol)
            
        if not quote:
            return jsonify({
                'status': 'error',
                'message': f'No quote data available for {symbol}'
            }), 404
            
        return jsonify({
            'status': 'success',
            'symbol': symbol.upper(),
            'quote': {
                'bid': quote.bid,
                'ask': quote.ask,
                'last': quote.last,
                'volume': quote.volume,
                'timestamp': quote.timestamp.isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Error getting quote for {symbol}: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving quote data for {symbol}'
        }), 500

@bp.route('/subscribe', methods=['POST'])
def subscribe_to_symbols():
    """
    Subscribe to real-time updates for symbols.
    
    Expected JSON payload:
        {
            "symbols": ["SPY", "AAPL", ...]
        }
        
    Returns:
        JSON with subscription status
    """
    try:
        # Parse request data
        data = request.get_json()
        if not data or 'symbols' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Missing symbols in request'
            }), 400
            
        symbols = data['symbols']
        
        # Get real-time data service
        market_feed = get_market_feed()
        
        # Start an asyncio background task to subscribe
        # In a real implementation, we'd use an async task queue
        import asyncio
        asyncio.create_task(market_feed.subscribe(symbols))
        
        return jsonify({
            'status': 'success',
            'message': f'Subscribed to {len(symbols)} symbols',
            'symbols': symbols
        })
    except Exception as e:
        logger.error(f"Error subscribing to symbols: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Error subscribing to symbols'
        }), 500

@bp.route('/popular-tickers', methods=['GET'])
def get_popular_tickers():
    """
    Get a list of popular tickers for quick selection.
    
    Returns:
        JSON with popular tickers
    """
    try:
        # In a real implementation, this would be dynamic based on
        # market activity or user preferences
        popular_tickers = [
            {"symbol": "SPY", "name": "SPDR S&P 500 ETF"},
            {"symbol": "QQQ", "name": "Invesco QQQ Trust"},
            {"symbol": "AAPL", "name": "Apple Inc."},
            {"symbol": "MSFT", "name": "Microsoft Corporation"},
            {"symbol": "AMZN", "name": "Amazon.com Inc."},
            {"symbol": "NVDA", "name": "NVIDIA Corporation"},
            {"symbol": "GOOGL", "name": "Alphabet Inc. Class A"},
            {"symbol": "TSLA", "name": "Tesla Inc."},
            {"symbol": "META", "name": "Meta Platforms Inc."},
            {"symbol": "AMD", "name": "Advanced Micro Devices"}
        ]
        
        return jsonify({
            'status': 'success',
            'tickers': popular_tickers
        })
    except Exception as e:
        logger.error(f"Error getting popular tickers: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Error retrieving popular tickers'
        }), 500

def register_routes(app):
    """Register market API routes with the Flask app."""
    app.register_blueprint(bp)
    logger.info("Market API routes registered")
@bp.route('/test/price-update/<symbol>', methods=['GET'])
def test_price_update(symbol):
    """Test price update publishing"""
    try:
        # Get latest price
        price = get_latest_quote(symbol)
        if not price:
            return jsonify({'error': 'Could not fetch price'}), 400
            
        # Update price cache and publish event
        timestamp = datetime.now()
        update_price_cache(symbol, price['last_price'], timestamp)
        
        return jsonify({
            'symbol': symbol,
            'price': price['last_price'],
            'timestamp': timestamp.isoformat(),
            'status': 'published'
        })
    except Exception as e:
        logger.error(f"Error testing price update: {e}")
        return jsonify({'error': str(e)}), 500
@bp.route('/test/event-publish', methods=['POST'])
def test_event_publish():
    """Test event publication system"""
    try:
        data = request.get_json()
        channel = data.get('channel', 'test:events')
        event_data = data.get('data', {'test': True})
        
        success = publish_event(channel, event_data)
        
        return jsonify({
            'success': success,
            'channel': channel,
            'data': event_data
        })
    except Exception as e:
        logger.error(f"Error testing event publish: {e}")
        return jsonify({'error': str(e)}), 500
