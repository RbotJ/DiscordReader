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

def add_todays_tickers_route(app, db):
    """
    Add the route for today's tickers to the Flask app.
    
    Args:
        app: Flask application
        db: SQLAlchemy database
    """
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