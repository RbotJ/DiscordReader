"""
TradeSetup Converter Service

Converts between the refactored TradeSetup dataclass and database models.
Provides clean separation between parsing logic and database persistence.
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .aplus_parser import TradeSetup as ParsedTradeSetup
from .models import TradeSetup as TradeSetupModel, ParsedLevel
from common.db import db

logger = logging.getLogger(__name__)


def convert_parsed_setup_to_model(
    parsed_setup: ParsedTradeSetup, 
    message_id: str,
    bias_note: Optional[str] = None
) -> TradeSetupModel:
    """
    Convert a parsed TradeSetup dataclass to a database model instance.
    
    Args:
        parsed_setup: TradeSetup from the refactored parser
        message_id: Discord message ID
        bias_note: Optional bias note for this ticker
        
    Returns:
        TradeSetupModel ready for database persistence
    """
    # Create the database model instance
    setup_model = TradeSetupModel(
        id=parsed_setup.id,
        message_id=message_id,
        ticker=parsed_setup.ticker,
        trading_day=parsed_setup.trading_day,
        index=parsed_setup.index,
        trigger_level=parsed_setup.trigger_level,
        target_prices=parsed_setup.target_prices,
        direction=parsed_setup.direction,
        label=parsed_setup.label,
        keywords=parsed_setup.keywords,
        emoji_hint=parsed_setup.emoji_hint,
        raw_line=parsed_setup.raw_line,
        # Legacy fields for backward compatibility
        setup_type=parsed_setup.label,  # Use label as setup_type
        profile_name=parsed_setup.label,  # Same as label
        bias_note=bias_note,
        # Status and confidence
        active=True,
        confidence_score=0.8,  # A+ setups are high confidence
        # Metadata
        parsed_metadata={
            'parser_version': 'refactored_v1',
            'keyword_matches': parsed_setup.keywords,
            'emoji_detected': parsed_setup.emoji_hint,
            'target_count': len(parsed_setup.target_prices)
        }
    )
    
    return setup_model


def create_levels_for_setup(setup_model: TradeSetupModel) -> List[ParsedLevel]:
    """
    Create ParsedLevel instances for a TradeSetup model.
    
    Args:
        setup_model: TradeSetupModel instance
        
    Returns:
        List of ParsedLevel instances for targets and entry
    """
    levels = []
    
    # Create entry level
    entry_level = ParsedLevel(
        setup_id=setup_model.id,
        level_type='entry',
        direction=setup_model.direction,
        trigger_price=setup_model.trigger_level,
        strategy=setup_model.label,
        confidence=0.8,
        description=f"Entry trigger for {setup_model.label or 'setup'}",
        active=True,
        triggered=False
    )
    levels.append(entry_level)
    
    # Create target levels
    for i, target_price in enumerate(setup_model.target_prices):
        target_level = ParsedLevel(
            setup_id=setup_model.id,
            level_type='target',
            direction=setup_model.direction,
            trigger_price=target_price,
            sequence_order=i + 1,
            strategy=setup_model.label,
            confidence=0.8,
            description=f"Target {i+1} for {setup_model.label or 'setup'}",
            active=True,
            triggered=False
        )
        levels.append(target_level)
    
    return levels


def save_parsed_setups_to_database(
    parsed_setups: List[ParsedTradeSetup], 
    message_id: str,
    ticker_bias_notes: Optional[Dict[str, str]] = None
) -> List[TradeSetupModel]:
    """
    Save a list of parsed setups to the database.
    
    Args:
        parsed_setups: List of TradeSetup dataclasses from parser
        message_id: Discord message ID
        ticker_bias_notes: Optional dict of bias notes per ticker
        
    Returns:
        List of saved TradeSetupModel instances
    """
    saved_setups = []
    ticker_bias_notes = ticker_bias_notes or {}
    
    try:
        for parsed_setup in parsed_setups:
            # Get bias note for this ticker
            bias_note = ticker_bias_notes.get(parsed_setup.ticker)
            
            # Convert to database model
            setup_model = convert_parsed_setup_to_model(
                parsed_setup, 
                message_id, 
                bias_note
            )
            
            # Check if setup already exists (upsert logic)
            existing_setup = TradeSetupModel.query.filter_by(id=setup_model.id).first()
            if existing_setup:
                logger.info(f"Setup {setup_model.id} already exists, updating...")
                # Update existing setup
                existing_setup.trigger_level = setup_model.trigger_level
                existing_setup.target_prices = setup_model.target_prices
                existing_setup.direction = setup_model.direction
                existing_setup.label = setup_model.label
                existing_setup.keywords = setup_model.keywords
                existing_setup.emoji_hint = setup_model.emoji_hint
                existing_setup.raw_line = setup_model.raw_line
                existing_setup.bias_note = setup_model.bias_note
                existing_setup.updated_at = datetime.utcnow()
                setup_model = existing_setup
            else:
                # Add new setup
                db.session.add(setup_model)
            
            # Create and add levels
            levels = create_levels_for_setup(setup_model)
            for level in levels:
                # Check if level already exists
                existing_level = ParsedLevel.query.filter_by(
                    setup_id=level.setup_id,
                    level_type=level.level_type,
                    trigger_price=level.trigger_price
                ).first()
                
                if not existing_level:
                    db.session.add(level)
            
            saved_setups.append(setup_model)
        
        # Commit all changes
        db.session.commit()
        logger.info(f"Successfully saved {len(saved_setups)} setups to database")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving setups to database: {e}")
        raise
    
    return saved_setups


def get_setups_by_message_id(message_id: str) -> List[TradeSetupModel]:
    """
    Retrieve all setups for a specific Discord message.
    
    Args:
        message_id: Discord message ID
        
    Returns:
        List of TradeSetupModel instances
    """
    return TradeSetupModel.query.filter_by(message_id=message_id).all()


def convert_model_to_dict(setup_model: TradeSetupModel) -> Dict[str, Any]:
    """
    Convert a TradeSetupModel to a dictionary for API responses.
    
    Args:
        setup_model: TradeSetupModel instance
        
    Returns:
        Dictionary representation suitable for JSON serialization
    """
    return setup_model.to_dict()