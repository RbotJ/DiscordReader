"""
Update the API routes to add today's tickers endpoint and candle data
"""
import logging
from flask import jsonify, request
from sqlalchemy import text
from datetime import date, datetime, timedelta
import json
import random
import numpy as np
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
import os
from alpaca.data.enums import Adjustment

# Helper function to get price levels for a ticker from the database
def get_ticker_price_levels(ticker, db):
    """
    Get price levels for a ticker from the database.
    
    Args:
        ticker: The ticker symbol
        db: SQLAlchemy database instance
        
    Returns:
        Dictionary with price levels or None if not found
    """
    try:
        # Get today's date
        today = date.today().isoformat()
        
        # Query the database for today's message
        query = text("""
            SELECT id, date, raw_text, source, created_at
            FROM setup_messages
            WHERE date = :today
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        result = db.session.execute(query, {'today': today})
        message = result.fetchone()
        
        # If no message for today, get the most recent message
        if not message:
            query = text("""
                SELECT id, date, raw_text, source, created_at
                FROM setup_messages
                ORDER BY created_at DESC
                LIMIT 1
            """)
            result = db.session.execute(query)
            message = result.fetchone()
        
        if not message:
            return None
        
        # Parse the message to extract ticker data
        from ticker_parser import parse_setup_message
        ticker_data = parse_setup_message(message[2], message[1])
        
        # Return the data for the requested ticker
        if ticker in ticker_data:
            return ticker_data[ticker]
        
        return None
        
    except Exception as e:
        logging.error(f"Error getting price levels for {ticker}: {e}")
        return None

# Generate synthetic candles based on ticker price levels
def generate_synthetic_candles(ticker, price_data, timeframe, limit):
    """
    Generate synthetic candle data based on ticker price levels.
    
    Args:
        ticker: The ticker symbol
        price_data: Dictionary with price levels
        timeframe: Candle timeframe string
        limit: Number of candles to generate
        
    Returns:
        List of candle dictionaries
    """
    candles = []
    
    # Use price levels to create realistic-looking data
    # Get the center price point (average of rejection and bounce)
    bounce_level = price_data.get('bounce', None)
    rejection_level = price_data.get('rejection', None)
    
    if bounce_level is None or rejection_level is None:
        # Use any available price level if bounce or rejection isn't available
        available_levels = [
            price_data.get('aggressive_breakdown'),
            price_data.get('conservative_breakdown'),
            price_data.get('aggressive_breakout'),
            price_data.get('conservative_breakout')
        ]
        available_levels = [level for level in available_levels if level is not None]
        
        if not available_levels:
            return []
        
        # Use the average as the center price
        center_price = sum(available_levels) / len(available_levels)
    else:
        center_price = (bounce_level + rejection_level) / 2
    
    # Determine price range
    if rejection_level and bounce_level:
        price_range = abs(rejection_level - bounce_level)
    else:
        # Use a default range of 2% of center price
        price_range = center_price * 0.02
    
    # Determine candle interval
    if timeframe == '1Min':
        interval_minutes = 1
    elif timeframe == '5Min':
        interval_minutes = 5
    elif timeframe == '15Min':
        interval_minutes = 15
    elif timeframe == '30Min':
        interval_minutes = 30
    elif timeframe == '1Hour':
        interval_minutes = 60
    else:
        interval_minutes = 5
    
    # Generate candles
    end_time = datetime.now()
    
    for i in range(limit):
        # Create timestamp
        timestamp = end_time - timedelta(minutes=interval_minutes * i)
        
        # Calculate price with some randomness
        volatility = price_range * 0.1  # 10% of price range for volatility
        random_walk = (np.random.random() - 0.5) * volatility
        
        # Create price trends based on price levels
        # Simulate price approaching rejection level and bouncing from bounce level
        progress = i / limit
        price_trend = center_price + (price_range * 0.5 * np.sin(progress * np.pi))
        
        # Add small random variations
        base_price = price_trend + random_walk
        
        # Generate OHLC values
        open_price = base_price
        high_price = base_price + (volatility * np.random.random() * 0.5)
        low_price = base_price - (volatility * np.random.random() * 0.5)
        close_price = base_price + (volatility * (np.random.random() - 0.5))
        
        # Generate volume
        volume = int(1000 + 9000 * np.random.random())
        
        # Create candle
        candle = {
            't': timestamp.isoformat(),
            'o': round(open_price, 2),
            'h': round(max(high_price, open_price, close_price), 2),
            'l': round(min(low_price, open_price, close_price), 2),
            'c': round(close_price, 2),
            'v': volume
        }
        
        candles.append(candle)
    
    # Reverse to get chronological order
    candles.reverse()
    
    return candles

def add_todays_tickers_route(app, db):
    """
    Add the route for today's tickers to the Flask app.
    
    Args:
        app: Flask application
        db: SQLAlchemy database
    """
    
    # Initialize historical data client for Alpaca
    ALPACA_API_KEY = os.environ.get('ALPACA_API_KEY', '')
    ALPACA_API_SECRET = os.environ.get('ALPACA_API_SECRET', '')
    
    try:
        stock_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_API_SECRET)
    except Exception as e:
        logging.error(f"Failed to initialize Alpaca historical data client: {e}")
        stock_client = None
    @app.route('/api/todays_tickers')
    def get_todays_tickers():
        """
        Get today's active trading tickers with price levels from Discord messages.
        
        Returns a list of tickers with their key price levels for today's trading session.
        """
        try:
            today = date.today().isoformat()
            
            # Import the ticker parser
            from ticker_parser import parse_setup_message
            
            # Query the database for today's message
            query = text("""
                SELECT id, date, raw_text, source, created_at
                FROM setup_messages
                WHERE date = :today
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            result = db.session.execute(query, {'today': today})
            message = result.fetchone()
            
            # If no message for today, get the most recent message
            if not message:
                query = text("""
                    SELECT id, date, raw_text, source, created_at
                    FROM setup_messages
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                result = db.session.execute(query)
                message = result.fetchone()
            
            if not message:
                return jsonify({
                    "status": "success",
                    "count": 0,
                    "tickers": [],
                    "message": "No active tickers found"
                })
            
            # Parse the message to extract ticker data
            ticker_data = parse_setup_message(message[2], message[1])
            
            # Convert to a list format for the API
            tickers_list = []
            for ticker, data in ticker_data.items():
                tickers_list.append({
                    "symbol": ticker,
                    "date": data['date'],
                    "price_levels": {
                        "rejection": data['rejection'],
                        "aggressive_breakdown": data['aggressive_breakdown'],
                        "conservative_breakdown": data['conservative_breakdown'],
                        "aggressive_breakout": data['aggressive_breakout'],
                        "conservative_breakout": data['conservative_breakout'],
                        "bounce": data['bounce']
                    },
                    "note": data['note']
                })
            
            return jsonify({
                "status": "success",
                "count": len(tickers_list),
                "tickers": tickers_list,
                "message_date": message[1]
            })
            
        except Exception as e:
            logging.error(f"Error fetching today's tickers: {e}")
            return jsonify({
                "status": "error",
                "message": "Failed to fetch today's active tickers"
            }), 500
            
    @app.route('/api/candles/<ticker>')
    def get_candle_data(ticker):
        """
        Get candle data for a ticker.
        
        Args:
            ticker: Ticker symbol
            
        Query params:
            timeframe: Candle timeframe (default: 5Min)
            limit: Number of candles to return (default: 100)
        """
        try:
            # Get query parameters
            timeframe_str = request.args.get('timeframe', '5Min')
            limit = int(request.args.get('limit', 100))
            
            # Parse timeframe for Alpaca
            # Using string representation for TimeFrame to avoid import issues
            if timeframe_str == '1Min':
                timeframe = '1Min'
            elif timeframe_str == '5Min':
                timeframe = '5Min'
            elif timeframe_str == '15Min':
                timeframe = '15Min'
            elif timeframe_str == '30Min':
                timeframe = '30Min'
            elif timeframe_str == '1Hour':
                timeframe = '1Hour'
            elif timeframe_str == '1Day':
                timeframe = '1Day'
            else:
                timeframe = '5Min'  # Default
            
            # Calculate start and end times for Eastern Time (4am to 12pm)
            now = datetime.now()
            
            # Create Eastern timezone
            import pytz
            eastern = pytz.timezone('US/Eastern')
            
            # Get current time in Eastern timezone
            current_eastern = now.astimezone(eastern)
            
            # Set end time to 12pm today in Eastern time
            today_noon_eastern = eastern.localize(
                datetime(
                    current_eastern.year,
                    current_eastern.month,
                    current_eastern.day,
                    12, 0, 0
                )
            )
            
            # If current time is past noon, use 12pm as end time, otherwise use current time
            if current_eastern.hour >= 12:
                end = today_noon_eastern
            else:
                end = current_eastern
                
            # Set start time to 4am today in Eastern time (premarket)
            start = eastern.localize(
                datetime(
                    current_eastern.year,
                    current_eastern.month,
                    current_eastern.day,
                    4, 0, 0
                )
            )
            
            # Convert to UTC for Alpaca API
            start = start.astimezone(pytz.UTC)
            end = end.astimezone(pytz.UTC)
            
            # If we have a valid stock client, try to get real data
            if stock_client:
                try:
                    # Get the proper TimeFrame for Alpaca API
                    # The TimeFrame class in alpaca-py needs to be instantiated with the right values
                    # For version compatibility, we'll create manually with string manipulation
                    minutes_map = {
                        '1Min': 1,
                        '5Min': 5,
                        '15Min': 15,
                        '30Min': 30
                    }
                    hours_map = {
                        '1Hour': 1,
                        '2Hour': 2,
                        '4Hour': 4
                    }
                    days_map = {
                        '1Day': 1
                    }
                    
                    # Create string-based timeframe for version compatibility
                    if timeframe in minutes_map:
                        minutes = minutes_map[timeframe]
                        tf = f"{minutes}Min" 
                    elif timeframe in hours_map:
                        hours = hours_map[timeframe]
                        tf = f"{hours}Hour"
                    elif timeframe in days_map:
                        days = days_map[timeframe]
                        tf = f"{days}Day"
                    else:
                        # Default to 5 minute candles
                        tf = "5Min"
                    
                    # Use correct TimeFrame objects for Alpaca API v0.40.0
                    if timeframe == '1Min':
                        tf_obj = TimeFrame(1, 'Min')
                    elif timeframe == '5Min':
                        tf_obj = TimeFrame(5, 'Min')
                    elif timeframe == '15Min':
                        tf_obj = TimeFrame(15, 'Min')
                    elif timeframe == '30Min':
                        tf_obj = TimeFrame(30, 'Min')
                    elif timeframe == '1Hour':
                        tf_obj = TimeFrame(1, 'Hour')
                    elif timeframe == '1Day':
                        tf_obj = TimeFrame(1, 'Day')
                    else:
                        # Default to 5 minute candles
                        tf_obj = TimeFrame(5, 'Min')
                    
                    # Make the request to Alpaca
                    bars_request = StockBarsRequest(
                        symbol_or_symbols=[ticker],
                        timeframe=tf_obj,
                        start=start,
                        end=end,
                        limit=limit
                    )
                    bars_data = stock_client.get_stock_bars(bars_request)
                    
                    # Convert to list of candles
                    candles = []
                    if bars_data and ticker in bars_data:
                        for bar in bars_data[ticker]:
                            candles.append({
                                't': bar.timestamp.isoformat(),
                                'o': float(bar.open),
                                'h': float(bar.high),
                                'l': float(bar.low),
                                'c': float(bar.close),
                                'v': float(bar.volume)
                            })
                    
                    return jsonify({
                        "status": "success",
                        "ticker": ticker,
                        "timeframe": timeframe_str,
                        "candles": candles
                    })
                except Exception as api_error:
                    logging.error(f"Error fetching Alpaca data for {ticker}: {api_error}")
                    # Fall through to generate synthetic data for demo purposes
            
            # Generate synthetic data if Alpaca API is not available or fails
            # This simulates market data around the price levels
            price_data = get_ticker_price_levels(ticker, db)
            
            # If we have price levels, use them to create realistic-looking data
            if price_data:
                candles = generate_synthetic_candles(ticker, price_data, timeframe_str, limit)
            else:
                # If no price data, return empty result
                candles = []
            
            return jsonify({
                "status": "success",
                "ticker": ticker,
                "timeframe": timeframe_str,
                "candles": candles,
                "note": "Using generated data - connect Alpaca API for real market data"
            })
            
        except Exception as e:
            logging.error(f"Error fetching candle data for {ticker}: {e}")
            return jsonify({
                "status": "error",
                "message": f"Failed to fetch candle data for {ticker}"
            }), 500