"""
Discord Setup Handler Module

This module handles processing of trade setup messages from Discord,
parsing them into structured data, and storing them in the database.
"""
import logging
import re
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from features.discord.client import register_setup_callback, send_status_update
from features.setups.parser import parse_setup_message
from app import db
from common.models import TradeSetupMessage
from common.db_models import SetupModel, TickerSetupModel

logger = logging.getLogger(__name__)

def extract_setup_date(message_content: str, message_timestamp: datetime) -> date:
    """
    Extract the setup date from a message or fall back to the message date.
    
    Args:
        message_content: The message content
        message_timestamp: The message timestamp
    
    Returns:
        date: The extracted date
    """
    # Try to extract date from message format: "A+ Trade Setups (Wed, May 14)"
    date_pattern = r"A\+ Trade Setups \(([A-Za-z]+),\s+([A-Za-z]+)\s+(\d{1,2})\)"
    match = re.search(date_pattern, message_content)
    
    if match:
        try:
            # Extract day, month, and day of month
            day_name = match.group(1)
            month_name = match.group(2)
            day_of_month = int(match.group(3))
            
            # Get the current year from the message timestamp
            current_year = message_timestamp.year
            
            # Parse the date
            date_str = f"{day_of_month} {month_name} {current_year}"
            setup_date = datetime.strptime(date_str, "%d %b %Y").date()
            
            # If the extracted date is more than 30 days in the future,
            # it's likely from the previous year (e.g., for messages in January
            # referring to December setups)
            today = datetime.now().date()
            if (setup_date - today).days > 30:
                setup_date = datetime.strptime(f"{day_of_month} {month_name} {current_year-1}", 
                                             "%d %b %Y").date()
            
            # Verify the date is reasonable (not in the future)
            if setup_date > today:
                logger.warning(f"Extracted date {setup_date} is in the future, using message date instead")
                return message_timestamp.date()
                
            return setup_date
        except Exception as e:
            logger.error(f"Error parsing setup date: {e}")
            return message_timestamp.date()
    
    # If no date found, use the message timestamp
    return message_timestamp.date()

def handle_discord_setup_message(message_content: str, message_timestamp: datetime) -> Optional[SetupModel]:
    """
    Process a setup message from Discord.
    
    Args:
        message_content: The content of the Discord message
        message_timestamp: The timestamp of the message
    
    Returns:
        Optional[SetupModel]: The created database model, or None if processing failed
    """
    logger.info("Processing Discord setup message")
    
    try:
        # Extract setup date from message or use message date
        setup_date = extract_setup_date(message_content, message_timestamp)
        
        # Parse the setup message
        setup_message = parse_setup_message(message_content, source="discord")
        
        # Update the date with the extracted date
        setup_message.date = setup_date
        
        # Check if we have any valid setups
        if not setup_message.setups:
            logger.warning("No valid trading setups found in Discord message")
            return None
        
        # Store in database
        with db.session.begin():
            # Check if this message is already processed (by checking raw_text)
            existing_setup = SetupModel.query.filter_by(raw_text=message_content).first()
            if existing_setup:
                logger.info(f"Skipping already processed setup message (ID: {existing_setup.id})")
                return existing_setup
            
            # Create setup model
            setup = SetupModel()
            setup.date = setup_message.date
            setup.raw_text = setup_message.raw_text
            setup.source = setup_message.source
            setup.created_at = datetime.utcnow()
            
            db.session.add(setup)
            db.session.flush()  # Flush to get the ID
            
            # Create ticker setups
            ticker_symbols = []
            for ticker_setup in setup_message.setups:
                ticker = TickerSetupModel()
                ticker.setup_id = setup.id
                ticker.symbol = ticker_setup.symbol
                ticker.created_at = datetime.utcnow()
                ticker_symbols.append(ticker_setup.symbol)
                
                db.session.add(ticker)
                
                # Process signals and bias here...
                # (This code is similar to what's in features/setups/api.py - create_setup_from_message)
                
            # Commit will be automatic due to with db.session.begin()
            
            # Send status update to Discord
            send_status_update(f"Processed new trading setup for {setup.date.strftime('%Y-%m-%d')} with {len(ticker_symbols)} tickers: {', '.join(ticker_symbols[:5])}{' and more' if len(ticker_symbols) > 5 else ''}")
            
            logger.info(f"Successfully processed Discord setup message with ID {setup.id}")
            return setup
            
    except Exception as e:
        logger.exception(f"Error processing Discord setup message: {e}")
        return None

def register_discord_setup_handler():
    """Register the callback for Discord setup messages."""
    register_setup_callback(handle_discord_setup_message)
    logger.info("Registered Discord setup message handler")