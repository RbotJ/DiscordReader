"""
Today's Active Tickers API

This module adds functionality to display today's active tickers from Discord messages.
"""
from flask import Blueprint, jsonify
from datetime import date
from sqlalchemy import text

bp = Blueprint('tickers', __name__, url_prefix='/api')

def register_tickers_api(app, db):
    """Register the tickers API routes with the Flask application."""
    app.register_blueprint(bp)
    
    @bp.route('/todays_tickers')
    def get_todays_tickers():
        """
        Get today's active trading tickers with price levels from Discord messages.
        
        Returns a list of tickers with their key price levels for today's trading session.
        """
        try:
            today = date.today().isoformat()
            
            # Query the database for today's message
            with db.engine.connect() as conn:
                # Get today's messages
                query = text("""
                    SELECT id, raw_text, date
                    FROM setup_messages
                    WHERE date = :today
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                
                result = conn.execute(query, {'today': today})
                message = result.fetchone()
                
                # If no message for today, get the most recent message
                if not message:
                    query = text("""
                        SELECT id, raw_text, date
                        FROM setup_messages
                        ORDER BY created_at DESC
                        LIMIT 1
                    """)
                    result = conn.execute(query)
                    message = result.fetchone()
            
            if not message:
                return jsonify({
                    "status": "success",
                    "count": 0,
                    "tickers": [],
                    "message": "No active tickers found"
                })
            
            # Parse the message to extract ticker data
            ticker_data = parse_setup_message(message[1], message[2])
            
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
                "message_date": message[2]
            })
            
        except Exception as e:
            import logging
            logging.error(f"Error fetching today's tickers: {e}")
            return jsonify({
                "status": "error",
                "message": "Failed to fetch today's active tickers"
            }), 500

def parse_setup_message(message_text, message_date):
    """
    Parse a setup message to extract tickers and price levels.
    
    Args:
        message_text: Raw message text
        message_date: Date of the message
        
    Returns:
        Dict of tickers and their price levels
    """
    try:
        # Dictionary to store ticker data
        ticker_data = {}
        
        # Common ticker symbols we're looking for
        common_tickers = ['SPY', 'TSLA', 'NVDA', 'QQQ', 'AAPL', 'MSFT', 'AMZN', 'META', 'GOOG', 'NFLX']
        
        # First split by double newlines to get potential sections
        raw_sections = message_text.split('\n\n')
        
        # Identify ticker sections
        sections = []
        for section in raw_sections:
            section = section.strip()
            if not section:
                continue
                
            # Check if this section starts with a known ticker
            found_ticker = None
            
            # Try to find the ticker at the beginning of the section
            for ticker in common_tickers:
                if section.startswith(ticker) or f"✅ {ticker}" in section or f"{ticker}" in section[:15]:
                    found_ticker = ticker
                    break
                    
            # Also support numbered format like "1) SPY" or "1. SPY"
            if not found_ticker:
                for ticker in common_tickers:
                    if f") {ticker}" in section[:15] or f". {ticker}" in section[:15]:
                        found_ticker = ticker
                        break
            
            if found_ticker:
                # Start a new section for this ticker
                sections.append((found_ticker, section))
        
        # Process each ticker section to extract price levels
        for ticker, section in sections:
            # Initialize data structure for this ticker
            ticker_data[ticker] = {
                'rejection': None,
                'aggressive_breakdown': None,
                'conservative_breakdown': None,
                'aggressive_breakout': None,
                'conservative_breakout': None,
                'bounce': None,
                'note': None,
                'date': message_date
            }
            
            # Analyze each line in the section
            lines = section.split('\n')
            for line in lines:
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Extract rejection level
                if '❌ Rejection Near' in line or 'Rejection Near' in line:
                    price_str = line.split('Near')[1].strip().split()[0].replace('(', '')
                    try:
                        ticker_data[ticker]['rejection'] = float(price_str)
                    except ValueError:
                        pass
                
                # Extract aggressive breakdown
                if '🔻 Aggressive Breakdown Below' in line or 'Aggressive Breakdown Below' in line:
                    price_str = line.split('Below')[1].strip().split()[0].replace('(', '')
                    try:
                        ticker_data[ticker]['aggressive_breakdown'] = float(price_str)
                    except ValueError:
                        pass
                
                # Extract conservative breakdown
                if '🔻 Conservative Breakdown Below' in line or 'Conservative Breakdown Below' in line:
                    price_str = line.split('Below')[1].strip().split()[0].replace('(', '')
                    try:
                        ticker_data[ticker]['conservative_breakdown'] = float(price_str)
                    except ValueError:
                        pass
                
                # Extract aggressive breakout
                if '🔼 Aggressive Breakout Above' in line or 'Aggressive Breakout Above' in line:
                    price_str = line.split('Above')[1].strip().split()[0].replace('(', '')
                    try:
                        ticker_data[ticker]['aggressive_breakout'] = float(price_str)
                    except ValueError:
                        pass
                
                # Extract conservative breakout
                if '🔼 Conservative Breakout Above' in line or 'Conservative Breakout Above' in line:
                    price_str = line.split('Above')[1].strip().split()[0].replace('(', '')
                    try:
                        ticker_data[ticker]['conservative_breakout'] = float(price_str)
                    except ValueError:
                        pass
                
                # Extract bounce level
                if '🔄 Bounce From' in line or 'Bounce From' in line:
                    price_str = line.split('From')[1].strip().split()[0].replace('(', '')
                    try:
                        ticker_data[ticker]['bounce'] = float(price_str)
                    except ValueError:
                        pass
                
                # Extract warning/note
                if '⚠️' in line or line.startswith('Note:') or line.startswith('Warning:'):
                    ticker_data[ticker]['note'] = line
        
        return ticker_data
        
    except Exception as e:
        import logging
        logging.error(f"Error parsing setup message: {e}")
        return {}