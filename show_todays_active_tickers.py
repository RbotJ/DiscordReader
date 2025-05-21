#!/usr/bin/env python3
"""
Show Today's Active Tickers

This script displays the active trading tickers from today's Discord messages,
along with their key price levels for breakouts, breakdowns, and bounces.
"""
import os
import logging
from datetime import datetime, date
import json
from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_todays_active_tickers():
    """
    Get tickers and their price levels from today's messages.
    
    Returns:
        Dict of tickers and their price levels
    """
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return None
    
    today = date.today().isoformat()
    
    try:
        # Create engine and connect to the database
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
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
            
            if not message:
                # If no message for today, get the most recent message
                query = text("""
                    SELECT id, raw_text, date
                    FROM setup_messages
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                result = conn.execute(query)
                message = result.fetchone()
                
            if not message:
                logger.warning("No messages found in database")
                return None
                
            # Extract tickers and price levels from the message
            return parse_setup_message(message[1], message[2])
            
    except Exception as e:
        logger.error(f"Error getting today's active tickers: {e}")
        return None

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
        
        # Split message into sections (one section per ticker)
        sections = []
        current_section = None
        
        # Common ticker symbols we're looking for
        common_tickers = ['SPY', 'TSLA', 'NVDA', 'QQQ', 'AAPL', 'MSFT', 'AMZN', 'META', 'GOOG', 'NFLX']
        
        # First split by double newlines to get potential sections
        raw_sections = message_text.split('\n\n')
        
        # Identify ticker sections
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
        logger.error(f"Error parsing setup message: {e}")
        return None

def format_price(price):
    """Format a price value for display"""
    if price is None:
        return "N/A"
    return f"${price:.2f}"

def display_ticker_data(ticker_data):
    """Display ticker data in a formatted way"""
    if not ticker_data:
        print("No ticker data available for today.")
        return
    
    print("\n===== TODAY'S ACTIVE TRADE TICKERS =====")
    print(f"Date: {ticker_data[next(iter(ticker_data))]['date']}")
    print("")
    
    for ticker, data in ticker_data.items():
        print(f"TICKER: {ticker}")
        print(f"  Rejection Level: {format_price(data['rejection'])}")
        print(f"  Aggressive Breakdown: {format_price(data['aggressive_breakdown'])}")
        print(f"  Conservative Breakdown: {format_price(data['conservative_breakdown'])}")
        print(f"  Aggressive Breakout: {format_price(data['aggressive_breakout'])}")
        print(f"  Conservative Breakout: {format_price(data['conservative_breakout'])}")
        print(f"  Bounce Zone: {format_price(data['bounce'])}")
        
        if data['note']:
            print(f"  Note: {data['note']}")
        
        print("")

def main():
    """Main function to display today's active tickers"""
    ticker_data = get_todays_active_tickers()
    display_ticker_data(ticker_data)

if __name__ == "__main__":
    main()