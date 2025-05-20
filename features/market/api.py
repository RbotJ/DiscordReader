"""
Market Data API Module

This module provides API endpoints for retrieving market data,
including prices, candlestick data, and market status.
"""

import datetime
import logging
import random
import pandas as pd
import numpy as np
from flask import Blueprint, jsonify, request

# Create blueprint
bp = Blueprint('market_api', __name__, url_prefix='/api/market')
logger = logging.getLogger(__name__)

# Timeframe constants
TIMEFRAMES = {
    '1m': {'minutes': 1, 'display': '1 Minute'},
    '5m': {'minutes': 5, 'display': '5 Minutes'},
    '15m': {'minutes': 15, 'display': '15 Minutes'},
    '1h': {'minutes': 60, 'display': '1 Hour'},
    '1d': {'days': 1, 'display': '1 Day'}
}

@bp.route('/status', methods=['GET'])
def get_market_status():
    """
    Get the current market status.
    
    Returns:
        JSON response with market status information
    """
    try:
        # Get actual market status from Alpaca in a real implementation
        now = datetime.datetime.now()
        
        # Check if it's a weekday and during market hours (9:30 AM - 4:00 PM EST)
        is_weekday = now.weekday() < 5  # 0-4 are weekdays
        market_open_time = now.replace(hour=9, minute=30, second=0)
        market_close_time = now.replace(hour=16, minute=0, second=0)
        is_market_hours = market_open_time <= now <= market_close_time
        
        is_open = is_weekday and is_market_hours
        
        # Calculate next open/close times
        if not is_weekday:
            # If it's weekend, next open is Monday
            days_to_monday = 7 - now.weekday()
            next_open = (now + datetime.timedelta(days=days_to_monday)).replace(
                hour=9, minute=30, second=0
            )
            next_close = next_open.replace(hour=16, minute=0, second=0)
        elif now < market_open_time:
            # Before market open today
            next_open = market_open_time
            next_close = market_close_time
        elif now > market_close_time:
            # After market close today, next is tomorrow or Monday
            if now.weekday() == 4:  # Friday
                next_open = (now + datetime.timedelta(days=3)).replace(
                    hour=9, minute=30, second=0
                )
            else:
                next_open = (now + datetime.timedelta(days=1)).replace(
                    hour=9, minute=30, second=0
                )
            next_close = next_open.replace(hour=16, minute=0, second=0)
        else:
            # During market hours
            next_open = None
            next_close = market_close_time
        
        return jsonify({
            'status': 'success',
            'is_open': is_open,
            'next_open': next_open.isoformat() if next_open else None,
            'next_close': next_close.isoformat() if next_close else None,
            'current_time': now.isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting market status: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Error retrieving market status'
        }), 500


@bp.route('/candles/<symbol>', methods=['GET'])
def get_candles(symbol):
    """
    Get candlestick data for a ticker symbol.
    
    Args:
        symbol: Ticker symbol
        
    Query parameters:
        timeframe: Candle timeframe (default: 5m)
        limit: Maximum number of candles to return (default: 100)
        date: Specific date for historical data (optional)
        
    Returns:
        JSON response with candlestick data
    """
    try:
        # Parse query parameters
        timeframe = request.args.get('timeframe', '5m')
        limit = int(request.args.get('limit', 100))
        date_str = request.args.get('date')
        
        if timeframe not in TIMEFRAMES:
            return jsonify({
                'status': 'error',
                'message': f'Invalid timeframe. Supported timeframes: {", ".join(TIMEFRAMES.keys())}'
            }), 400
        
        # Generate or fetch candle data from Alpaca
        try:
            # We'll fetch real data from Alpaca when available
            # For now, generate sample data for testing
            candle_data = generate_candle_data(symbol, timeframe, limit, date_str)
            
            # Format the response for frontend compatibility
            candles = []
            for timestamp, row in candle_data.iterrows():
                candle = {
                    'timestamp': timestamp.isoformat(),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': int(row['volume'])
                }
                candles.append(candle)
                
            return jsonify({
                'status': 'success',
                'symbol': symbol.upper(),
                'timeframe': timeframe,
                'candles': candles
            })
        except Exception as e:
            logger.error(f"Error processing candle data: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Error processing candle data'
            }), 500
    except Exception as e:
        logger.error(f"Error getting candles for {symbol}: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving candle data for {symbol}'
        }), 500


@bp.route('/quote/<symbol>', methods=['GET'])
def get_quote(symbol):
    """
    Get the latest quote for a ticker symbol.
    
    Args:
        symbol: Ticker symbol
        
    Returns:
        JSON response with latest quote data
    """
    try:
        # In a real implementation, this would fetch from Alpaca or another data provider
        symbol = symbol.upper()
        
        # Generate deterministic but varied price based on symbol
        base_price = 100 + hash(symbol) % 400
        jitter = random.uniform(-5, 5)
        price = round(base_price + jitter, 2)
        
        # Add bid/ask spread
        spread = round(price * 0.001, 2)  # 0.1% spread
        bid = round(price - spread / 2, 2)
        ask = round(price + spread / 2, 2)
        
        # Generate volume
        volume = random.randint(1000, 100000)
        
        return jsonify({
            'status': 'success',
            'symbol': symbol,
            'price': price,
            'bid': bid,
            'ask': ask,
            'volume': volume,
            'timestamp': datetime.datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting quote for {symbol}: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving quote for {symbol}'
        }), 500


def generate_candle_data(symbol, timeframe, limit, date_str=None):
    """
    Generate sample candlestick data for a ticker.
    
    In a real implementation, this would fetch from Alpaca or another data provider.
    
    Args:
        symbol: Ticker symbol
        timeframe: Candle timeframe
        limit: Maximum number of candles
        date_str: Optional specific date for historical data
        
    Returns:
        DataFrame with OHLCV data
    """
    # Set a seed based on the symbol for consistent demo data
    random.seed(hash(symbol))
    np.random.seed(hash(symbol))
    
    # Determine the time delta based on the timeframe
    time_delta = None
    if 'm' in timeframe:
        minutes = int(timeframe.replace('m', ''))
        time_delta = datetime.timedelta(minutes=minutes)
    elif 'h' in timeframe:
        hours = int(timeframe.replace('h', ''))
        time_delta = datetime.timedelta(hours=hours)
    elif 'd' in timeframe:
        days = int(timeframe.replace('d', ''))
        time_delta = datetime.timedelta(days=days)
    else:
        # Default to 5-minute candles
        time_delta = datetime.timedelta(minutes=5)
    
    # Determine the end time
    if date_str:
        try:
            # If a specific date is requested, use the market close time on that date
            end_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
            end_time = end_date.replace(hour=16, minute=0, second=0)
        except ValueError:
            # Invalid date format, use current time
            end_time = datetime.datetime.now()
    else:
        # Use current time
        end_time = datetime.datetime.now()
    
    # Generate timestamps for the candles
    timestamps = [end_time - i * time_delta for i in range(limit)]
    timestamps.reverse()  # Oldest first
    
    # Generate a realistic price series
    # Start with a base price based on the symbol
    base_price = 100 + hash(symbol) % 400
    
    # Create a random walk for the close prices
    volatility = base_price * 0.01  # 1% volatility
    close_prices = [base_price]
    
    for i in range(1, limit):
        # Random walk with momentum and mean reversion
        momentum = 0.7 * (close_prices[i-1] - base_price) / base_price
        mean_reversion = -0.3 * (close_prices[i-1] - base_price) / base_price
        random_factor = np.random.normal(0, 1) * volatility
        
        # Combine factors for the price change
        price_change = close_prices[i-1] * (momentum + mean_reversion + random_factor)
        new_price = close_prices[i-1] + price_change
        
        # Ensure price stays positive
        new_price = max(new_price, 0.01)
        
        close_prices.append(new_price)
    
    # Generate open, high, low prices based on close prices
    open_prices = [close_prices[0]]
    high_prices = []
    low_prices = []
    
    for i in range(1, limit):
        # Prior close becomes open
        open_prices.append(close_prices[i-1])
        
        # High and low within the candle
        price_range = abs(close_prices[i] - open_prices[i]) * (1 + np.random.uniform(0.5, 2.0))
        if close_prices[i] >= open_prices[i]:
            # Bullish candle
            high_prices.append(close_prices[i] + price_range * np.random.uniform(0, 0.5))
            low_prices.append(open_prices[i] - price_range * np.random.uniform(0, 0.5))
        else:
            # Bearish candle
            high_prices.append(open_prices[i] + price_range * np.random.uniform(0, 0.5))
            low_prices.append(close_prices[i] - price_range * np.random.uniform(0, 0.5))
    
    # Add the high and low for the first candle
    first_price_range = abs(close_prices[0] - open_prices[0]) * (1 + np.random.uniform(0.5, 2.0))
    if close_prices[0] >= open_prices[0]:
        high_prices.insert(0, close_prices[0] + first_price_range * np.random.uniform(0, 0.5))
        low_prices.insert(0, open_prices[0] - first_price_range * np.random.uniform(0, 0.5))
    else:
        high_prices.insert(0, open_prices[0] + first_price_range * np.random.uniform(0, 0.5))
        low_prices.insert(0, close_prices[0] - first_price_range * np.random.uniform(0, 0.5))
    
    # Generate volumes (higher on big price moves)
    base_volume = np.random.randint(1000, 100000)
    volumes = []
    
    for i in range(limit):
        # Volume correlates with price volatility
        if i > 0:
            price_change_pct = abs(close_prices[i] - close_prices[i-1]) / close_prices[i-1]
            volume_multiplier = 1 + price_change_pct * 10  # More volume on bigger moves
        else:
            volume_multiplier = 1
        
        # Add some randomness to volume
        volume = int(base_volume * volume_multiplier * np.random.uniform(0.5, 1.5))
        volumes.append(volume)
    
    # Create a DataFrame
    data = {
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes
    }
    
    df = pd.DataFrame(data, index=timestamps)
    
    return df


def register_routes(app):
    """Register the market API routes with the Flask app."""
    app.register_blueprint(bp)
    logger.info("Market API routes registered")

# Expose market routes for importing in other modules
market_routes = bp