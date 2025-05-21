"""
API Routes Module

This module organizes and documents the API routes used by the trading application.
It follows a RESTful structure and the vertical slice architecture of the application.
"""

import logging
import json
from flask import jsonify, request
from datetime import datetime, date
import os
from sqlalchemy import text

def register_api_routes(app, db):
    """
    Register all API routes with the Flask application.
    
    This function serves as a centralized place to register all API routes
    for better organization and documentation.
    
    Args:
        app: Flask application instance
        db: SQLAlchemy database instance
    """
    
    # Import here to avoid circular imports
    from discord_message_storage import get_message_stats, get_latest_message, get_message_history
    # ------------------------------------------------------------------
    # Health and Status Routes
    # ------------------------------------------------------------------
    
    @app.route('/api/health')
    def health_check():
        """API health check endpoint."""
        return jsonify({
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "app": os.environ.get("REPL_SLUG", "aplus-trading-app"),
            "version": "0.1.0"
        })
    
    @app.route('/api/status')
    def system_status():
        """
        Get comprehensive system status.
        
        Returns status of all major components:
        - API
        - Database
        - Market data connections
        - Strategy detector
        - Execution engine
        - Redis
        - Discord integration
        """
        status = {
            "api": {
                "status": "ok",
                "timestamp": datetime.now().isoformat()
            },
            "components": {}
        }
        
        # Check strategy detector status
        try:
            from features.strategy.candle_detector import detector_running
            is_running = detector_running() if callable(detector_running) else True
            status["components"]["strategy_detector"] = {
                "status": "ok" if is_running else "error",
                "name": "Candle Pattern Detector",
                "running": is_running
            }
        except Exception as e:
            status["components"]["strategy_detector"] = {
                "status": "error",
                "name": "Candle Pattern Detector",
                "running": False,
                "error": str(e)
            }
            
        # Check execution service status
        try:
            from features.execution.options_trader import trader_running
            is_running = trader_running() if callable(trader_running) else True
            status["components"]["execution_service"] = {
                "status": "ok" if is_running else "error",
                "name": "Options Trader",
                "running": is_running
            }
        except Exception as e:
            status["components"]["execution_service"] = {
                "status": "error",
                "name": "Options Trader",
                "running": False,
                "error": str(e)
            }
            
        # Check market data status
        try:
            from features.market.price_monitor import monitor_running
            is_running = monitor_running() if callable(monitor_running) else True
            status["components"]["market_data"] = {
                "status": "ok" if is_running else "error",
                "name": "Price Monitor",
                "running": is_running
            }
        except Exception as e:
            status["components"]["market_data"] = {
                "status": "error",
                "name": "Price Monitor",
                "running": False,
                "error": str(e)
            }
            
        # Check Discord integration status
        try:
            from features.discord.client import client_connected
            is_connected = client_connected() if callable(client_connected) else True
            status["components"]["discord"] = {
                "status": "ok" if is_connected else "error",
                "name": "Discord Integration",
                "connected": is_connected
            }
        except Exception as e:
            status["components"]["discord"] = {
                "status": "error",
                "name": "Discord Integration",
                "connected": False,
                "error": str(e)
            }
            
        # Check database status
        try:
            # Simple test query to verify database connection
            from sqlalchemy import text
            db.session.execute(text("SELECT 1")).fetchone()
            status["components"]["database"] = {
                "status": "ok",
                "name": "PostgreSQL Database",
                "connected": True
            }
        except Exception as e:
            status["components"]["database"] = {
                "status": "error",
                "name": "PostgreSQL Database",
                "connected": False,
                "error": str(e)
            }
            
        # Check Redis status
        try:
            from common.redis_utils import ping_redis
            redis_ok = ping_redis() if callable(ping_redis) else True
            status["components"]["redis"] = {
                "status": "ok" if redis_ok else "error",
                "name": "Redis Cache",
                "connected": redis_ok
            }
        except Exception as e:
            status["components"]["redis"] = {
                "status": "error",
                "name": "Redis Cache",
                "connected": False,
                "error": str(e)
            }
        
        return jsonify(status)
    
    # ------------------------------------------------------------------
    # Account and Positions Routes
    # ------------------------------------------------------------------
    
    @app.route('/api/account')
    def get_account():
        """
        Get account information.
        Returns account balance, buying power, etc.
        """
        try:
            # Try to get account info from Alpaca
            from features.alpaca.client import get_account_info
            account = get_account_info()
            return jsonify(account)
        except Exception as e:
            logging.error(f"Error fetching account information: {e}")
            # Return fallback account info if there's an error
            return jsonify({
                'id': 'paper-account',
                'equity': 100000.00,
                'cash': 75000.00,
                'buying_power': 150000.00,
                'portfolio_value': 100000.00,
                'positions_count': 0,
                'status': 'ACTIVE'
            })
    
    @app.route('/api/execution/positions')
    def get_positions():
        """
        Get current positions.
        Returns a list of open positions.
        """
        try:
            # Try to get positions from Alpaca
            from features.alpaca.client import get_positions
            positions = get_positions()
            return jsonify({"positions": positions})
        except Exception as e:
            logging.error(f"Error fetching positions: {e}")
            return jsonify({"positions": []})
    
    @app.route('/api/execution/order', methods=['POST'])
    def place_order():
        """
        Place an order.
        
        Expected JSON payload:
        {
            "symbol": "SPY",
            "qty": 10,
            "side": "buy",  # or "sell"
            "type": "market",  # optional, defaults to "market"
            "time_in_force": "day",  # optional, defaults to "day"
            "limit_price": 450.0,  # required if type is "limit"
            "stop_price": 440.0,  # required if type is "stop" or "stop_limit"
        }
        """
        try:
            # Parse request JSON
            order_data = request.json
            
            if not order_data or 'symbol' not in order_data or 'qty' not in order_data or 'side' not in order_data:
                return jsonify({"success": False, "error": "Missing required fields"}), 400
            
            # Place order via Alpaca client
            from features.alpaca.client import place_equity_order
            order_result = place_equity_order(
                symbol=order_data['symbol'],
                qty=order_data['qty'],
                side=order_data['side'],
                order_type=order_data.get('type', 'market'),
                time_in_force=order_data.get('time_in_force', 'day'),
                limit_price=order_data.get('limit_price'),
                stop_price=order_data.get('stop_price')
            )
            
            return jsonify({"success": True, "order": order_result})
        except Exception as e:
            logging.error(f"Error placing order: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/execution/close/<symbol>', methods=['POST'])
    def close_position(symbol):
        """
        Close a position for a given symbol.
        
        Path params:
            symbol: The symbol to close the position for
            
        Query params or JSON body:
            percentage: Percentage of the position to close (0.0-1.0, default: 1.0)
        """
        try:
            # Get percentage from request
            percentage = 1.0  # Default to closing entire position
            
            if request.is_json:
                data = request.json
                percentage = float(data.get('percentage', 1.0))
            else:
                percentage = float(request.args.get('percentage', 1.0))
                
            # Validate percentage
            if percentage <= 0.0 or percentage > 1.0:
                return jsonify({"success": False, "error": "Percentage must be between 0.0 and 1.0"}), 400
            
            # Close position via Alpaca client
            from features.alpaca.client import close_position as alpaca_close_position
            result = alpaca_close_position(symbol, percentage)
            
            return jsonify({"success": True, "result": result})
        except Exception as e:
            logging.error(f"Error closing position for {symbol}: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    # ------------------------------------------------------------------
    # Market Data Routes
    # ------------------------------------------------------------------
    
    @app.route('/api/market/status')
    def get_market_status():
        """
        Get current market status.
        Returns whether the market is open, next open/close times, etc.
        """
        try:
            from features.market.client import get_market_status as get_status
            status = get_status()
            return jsonify(status)
        except Exception as e:
            logging.error(f"Error fetching market status: {e}")
            # Default status based on current time
            import datetime
            now = datetime.datetime.now()
            market_open = 9 <= now.hour <= 16
            return jsonify({
                'is_open': market_open,
                'next_close': (now + datetime.timedelta(hours=17 - now.hour)).isoformat() if market_open else None,
                'next_open': (now + datetime.timedelta(days=1, hours=9 - now.hour)).isoformat() if not market_open else None
            })
    
    @app.route('/api/market/candles/<ticker>')
    def get_candles(ticker):
        """
        Get candle data for a ticker.
        
        Args:
            ticker: Ticker symbol
            
        Query params:
            timeframe: Candle timeframe (default: 1Day)
            limit: Number of candles to return (default: 100)
        """
        timeframe = request.args.get('timeframe', '1Day')
        limit = int(request.args.get('limit', 100))
        
        try:
            # First try to get candles from historical data provider
            try:
                from features.market.historical_data import get_historical_candles
                candles = get_historical_candles(ticker, timeframe, limit)
                if candles and len(candles) > 0:
                    return jsonify({"candles": candles})
            except ImportError:
                logging.warning(f"Could not import historical data provider for {ticker}")
            
            # Fall back to Alpaca client if historical data not available
            from features.alpaca.client import get_bars
            candles = get_bars(ticker, timeframe, limit)
            return jsonify({"candles": candles or []})
        except Exception as e:
            logging.error(f"Error fetching candles for {ticker}: {e}")
            return jsonify({"candles": []})
    
    @app.route('/api/market/quote/<ticker>')
    def get_quote(ticker):
        """
        Get the latest quote for a ticker.
        
        Args:
            ticker: Ticker symbol
        """
        try:
            from features.market.client import get_latest_quote
            quote = get_latest_quote(ticker)
            return jsonify(quote)
        except Exception as e:
            logging.error(f"Error fetching quote for {ticker}: {e}")
            return jsonify({})
    
    # ------------------------------------------------------------------
    # Ticker and Symbol Routes
    # ------------------------------------------------------------------
    
    @app.route('/api/tickers')
    def get_tickers():
        """
        Get available tickers with trading setups.
        Returns a list of ticker symbols that have active setups.
        """
        try:
            # Use raw SQL to avoid model registry conflicts
            from sqlalchemy import text
            results = db.session.execute(text("SELECT DISTINCT symbol FROM ticker_setups")).fetchall()
            tickers = [row[0] for row in results]
            
            # If no tickers found in the database, return a few sample tickers
            if not tickers:
                tickers = ["SPY", "AAPL", "MSFT", "NVDA", "TSLA"]
            
            return jsonify(tickers)
        except Exception as e:
            logging.error(f"Error fetching tickers: {e}")
            return jsonify([])
    
    # ------------------------------------------------------------------
    # Strategy and Signal Routes
    # ------------------------------------------------------------------
    
    @app.route('/api/strategy/signals/<ticker>')
    def get_signals(ticker):
        """
        Get signals for a ticker.
        
        Args:
            ticker: Ticker symbol
        """
        try:
            # First check for active candle signals
            try:
                from features.strategy import get_candle_signals
                active_signals = get_candle_signals(ticker)
                
                if active_signals:
                    # Return all active candle signals
                    return jsonify({"signals": active_signals})
            except ImportError:
                logging.warning(f"Could not import candle signals module for {ticker}")
            
            # Fall back to database signals if no active candle signals
            try:
                from sqlalchemy import text
                import json
                
                # Use raw SQL to avoid model registry conflicts
                # First get the most recent ticker setup ID
                setup_query = text("""
                    SELECT id FROM ticker_setups 
                    WHERE symbol = :symbol 
                    ORDER BY id DESC LIMIT 1
                """)
                setup_result = db.session.execute(setup_query, {"symbol": ticker}).fetchone()
                
                if not setup_result:
                    return jsonify({"signals": []})
                
                setup_id = setup_result[0]
                
                # Then get signals for that ticker setup
                signals_query = text("""
                    SELECT id, category, aggressiveness, comparison, trigger, targets, created_at
                    FROM signals
                    WHERE ticker_setup_id = :setup_id
                """)
                signals = db.session.execute(signals_query, {"setup_id": setup_id}).fetchall()
                
                if not signals:
                    return jsonify({"signals": []})
                
                # Convert database signals to API format
                signal_list = []
                for signal in signals:
                    try:
                        # Parse JSON fields if they're strings
                        trigger_value = json.loads(signal[4]) if isinstance(signal[4], str) else signal[4]
                        targets = json.loads(signal[5]) if isinstance(signal[5], str) else signal[5]
                        
                        signal_data = {
                            'id': signal[0],
                            'ticker': ticker,
                            'category': signal[1],
                            'aggressiveness': signal[2],
                            'comparison': signal[3],
                            'trigger': trigger_value,
                            'targets': targets,
                            'status': 'pending',  # Default status
                            'source': 'database'
                        }
                        signal_list.append(signal_data)
                    except Exception as signal_error:
                        logging.error(f"Error processing signal {signal[0]}: {signal_error}")
                        continue
                
                return jsonify({"signals": signal_list})
            except Exception as db_error:
                logging.error(f"Database error fetching signals for {ticker}: {db_error}")
                return jsonify({"signals": []})
        except Exception as e:
            logging.error(f"Error fetching signals for {ticker}: {e}")
            return jsonify({"signals": []})
    
    @app.route('/api/strategy/signals/add', methods=['POST'])
    def add_signal():
        """
        Add a candle signal for testing.
        
        Expected JSON payload format:
        {
            "ticker": "SPY",
            "category": "breakout",  # or "breakdown", "rejection", "bounce"
            "trigger": {
                "price": 450.0,
                "timeframe": "15Min"
            },
            "targets": [
                {"price": 455.0, "percentage": 0.25},
                {"price": 460.0, "percentage": 0.5},
                {"price": 465.0, "percentage": 0.25}
            ],
            "status": "pending"
        }
        """
        try:
            # Parse request JSON
            signal_data = request.json
            
            if not signal_data or 'ticker' not in signal_data or 'trigger' not in signal_data:
                return jsonify({"success": False, "error": "Invalid signal data"}), 400
            
            # Add signal to candle detector
            from features.strategy import add_candle_signal
            success = add_candle_signal(signal_data)
            
            if success:
                return jsonify({"success": True, "message": f"Signal added for {signal_data['ticker']}"}), 201
            else:
                return jsonify({"success": False, "error": "Failed to add signal"}), 500
        except Exception as e:
            logging.error(f"Error adding signal: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/strategy/status')
    def strategy_status():
        """Get the status of the strategy detector."""
        try:
            # Check if the strategy detector is running
            from features.strategy.candle_detector import detector_running
            
            is_running = True
            try:
                # If the function exists, call it
                is_running = detector_running() if callable(detector_running) else True
            except (ImportError, AttributeError):
                # Function doesn't exist, assume running
                pass
                
            return jsonify({
                'status': 'success',
                'detector': {
                    'running': is_running,
                    'name': 'Candle Pattern Detector'
                }
            })
        except Exception as e:
            logging.error(f"Error checking strategy status: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e),
                'detector': {
                    'running': False,
                    'name': 'Candle Pattern Detector'
                }
            })
    
    # ------------------------------------------------------------------
    # Setup and Discord Message Routes
    # ------------------------------------------------------------------
    
    @app.route('/api/discord-messages')
    def get_discord_messages():
        """
        Get recent messages from Discord directly.
        Returns the most recent messages from the A+ setups channel.
        """
        try:
            # Import the Discord client function
            from features.discord.client import get_channel_messages
            
            # Get messages directly from Discord
            messages = get_channel_messages()
            
            # Return as JSON
            return jsonify({
                'status': 'success',
                'data': messages
            })
        except Exception as e:
            logging.error(f"Error fetching Discord messages: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/api/setups/recent')
    def get_recent_setups():
        """
        Get recent trading setups from the database.
        
        Query params:
            limit: Maximum number of setups to return (default: 10)
        """
        limit = int(request.args.get('limit', 10))
        
        try:
            # Use raw SQL to avoid model registry conflicts
            from sqlalchemy import text
            
            # Get recent setup messages
            query = text("""
                SELECT sm.id, sm.date, sm.raw_text, sm.source, sm.created_at
                FROM setup_messages sm
                ORDER BY sm.created_at DESC
                LIMIT :limit
            """)
            
            results = db.session.execute(query, {"limit": limit}).fetchall()
            
            # Format results
            setups = []
            for row in results:
                setup = {
                    'id': row[0],
                    'date': row[1].isoformat() if row[1] else None,
                    'text': row[2],
                    'source': row[3],
                    'created_at': row[4].isoformat() if row[4] else None
                }
                setups.append(setup)
                
            return jsonify({"setups": setups})
        except Exception as e:
            logging.error(f"Error fetching recent setups: {e}")
            return jsonify({"setups": []})
    
    @app.route('/api/setups/<int:setup_id>')
    def get_setup_detail(setup_id):
        """
        Get details for a specific setup.
        
        Args:
            setup_id: ID of the setup message
        """
        try:
            # Use raw SQL to avoid model registry conflicts
            from sqlalchemy import text
            
            # Get setup message
            message_query = text("""
                SELECT id, date, raw_text, source, created_at
                FROM setup_messages
                WHERE id = :id
            """)
            
            message_result = db.session.execute(message_query, {"id": setup_id}).fetchone()
            
            if not message_result:
                return jsonify({"error": "Setup not found"}), 404
                
            # Get ticker setups for this message
            tickers_query = text("""
                SELECT id, symbol, text, model_type
                FROM ticker_setups
                WHERE message_id = :message_id
            """)
            
            ticker_results = db.session.execute(tickers_query, {"message_id": setup_id}).fetchall()
            
            # Format the response
            setup = {
                'id': message_result[0],
                'date': message_result[1].isoformat() if message_result[1] else None,
                'text': message_result[2],
                'source': message_result[3],
                'created_at': message_result[4].isoformat() if message_result[4] else None,
                'tickers': []
            }
            
            for ticker in ticker_results:
                ticker_detail = {
                    'id': ticker[0],
                    'symbol': ticker[1],
                    'text': ticker[2],
                    'model_type': ticker[3],
                    'signals': []
                }
                
                # Get signals for this ticker setup
                signals_query = text("""
                    SELECT id, category, aggressiveness, comparison, trigger, targets
                    FROM signals
                    WHERE ticker_setup_id = :ticker_id
                """)
                
                signal_results = db.session.execute(signals_query, {"ticker_id": ticker[0]}).fetchall()
                
                # Format signals
                import json
                for signal in signal_results:
                    trigger_value = json.loads(signal[4]) if isinstance(signal[4], str) else signal[4]
                    targets = json.loads(signal[5]) if isinstance(signal[5], str) else signal[5]
                    
                    signal_detail = {
                        'id': signal[0],
                        'category': signal[1],
                        'aggressiveness': signal[2],
                        'comparison': signal[3],
                        'trigger': trigger_value,
                        'targets': targets,
                        'status': 'pending'  # Default status
                    }
                    ticker_detail['signals'].append(signal_detail)
                
                setup['tickers'].append(ticker_detail)
                
            return jsonify(setup)
        except Exception as e:
            logging.error(f"Error fetching setup details for ID {setup_id}: {e}")
            return jsonify({"error": str(e)}), 500
    
    # ------------------------------------------------------------------
    # Misc Testing and Utility Routes
    # ------------------------------------------------------------------
    
    @app.route('/api/test')
    def api_test():
        """Test API endpoints."""
        results = {}
        
        # Test account endpoint
        try:
            from features.alpaca.client import get_account_info
            account = get_account_info()
            results['account'] = {
                'status': 'success',
                'data': account
            }
        except Exception as e:
            results['account'] = {
                'status': 'error',
                'error': str(e)
            }
            
        # Test positions endpoint
        try:
            from features.alpaca.client import get_positions
            positions = get_positions()
            results['positions'] = {
                'status': 'success',
                'count': len(positions),
                'data': positions[:2] if positions else []  # Show first 2 positions only
            }
        except Exception as e:
            results['positions'] = {
                'status': 'error',
                'error': str(e)
            }
            
        # Test candles endpoint
        try:
            from features.alpaca.client import get_bars
            candles = get_bars('SPY', '1Min', 10)
            results['candles'] = {
                'status': 'success',
                'count': len(candles),
                'data': candles[:2] if candles else []  # Show only first 2 candles
            }
        except Exception as e:
            results['candles'] = {
                'status': 'error',
                'error': str(e)
            }
            
        # Test signals endpoint
        try:
            from features.strategy import get_candle_signals
            signals = get_candle_signals('SPY')
            results['signals'] = {
                'status': 'success',
                'count': len(signals) if signals else 0,
                'data': signals[:2] if signals else []  # Show only first 2 signals
            }
        except Exception as e:
            results['signals'] = {
                'status': 'error',
                'error': str(e)
            }
            
        return jsonify(results)