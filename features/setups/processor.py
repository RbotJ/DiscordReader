
"""
Setup Message Processor Module

This module processes raw setup messages and stores structured data in the database.
"""
import logging
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional

from app import db
from common.db_models import SetupModel, TickerSetupModel, SignalModel, BiasModel
from common.events import publish_event
from features.setups.parser import parse_setup_message

logger = logging.getLogger(__name__)

def parse_new_setup_messages() -> int:
    """
    Process all unparsed setup messages in the database.
    Returns the number of successfully processed messages.
    """
    processed_count = 0
    
    try:
        # Get all unparsed messages
        unparsed_messages = SetupModel.query.filter_by(parsed=False).all()
        logger.info(f"Found {len(unparsed_messages)} unparsed setup messages")
        
        for setup_model in unparsed_messages:
            try:
                # Parse the message
                setup_dto = parse_setup_message(
                    message_text=setup_model.raw_text,
                    setup_date=setup_model.date,
                    source=setup_model.source
                )
                
                if not setup_dto:
                    logger.warning(f"Could not parse setup message {setup_model.id}")
                    continue
                
                # Process each ticker setup
                for ticker_setup in setup_dto.ticker_setups:
                    # Create ticker setup record
                    db_ticker = TickerSetupModel(
                        setup_id=setup_model.id,
                        symbol=ticker_setup.symbol,
                        text=ticker_setup.text,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(db_ticker)
                    db.session.flush()  # Get ID without committing
                    
                    # Process signals
                    for signal in ticker_setup.signals:
                        db_signal = SignalModel(
                            ticker_setup_id=db_ticker.id,
                            category=signal.category.value,
                            aggressiveness=signal.aggressiveness.value,
                            comparison=signal.comparison.value,
                            trigger_value=signal.trigger,
                            targets=[float(t) for t in signal.targets],
                            active=True,
                            created_at=datetime.utcnow()
                        )
                        db.session.add(db_signal)
                    
                    # Process bias if present
                    if ticker_setup.bias:
                        db_bias = BiasModel(
                            ticker_setup_id=db_ticker.id,
                            direction=ticker_setup.bias.direction.value,
                            condition=ticker_setup.bias.condition.value,
                            price=float(ticker_setup.bias.price),
                            created_at=datetime.utcnow()
                        )
                        
                        # Add flip data if present
                        if ticker_setup.bias.flip:
                            db_bias.flip_direction = ticker_setup.bias.flip.direction.value
                            db_bias.flip_price_level = float(ticker_setup.bias.flip.price_level)
                        
                        db.session.add(db_bias)
                
                # Mark as parsed
                setup_model.parsed = True
                processed_count += 1
                
                # Commit changes for this message
                db.session.commit()
                
                # Publish event
                try:
                    publish_event('setup.parsed', {
                        'setup_id': setup_model.id,
                        'ticker_count': len(setup_dto.ticker_setups),
                        'source': setup_model.source
                    })
                except Exception as e:
                    logger.warning(f"Could not publish setup.parsed event: {e}")
                
            except SQLAlchemyError as e:
                logger.error(f"Database error processing setup {setup_model.id}: {e}")
                db.session.rollback()
            except Exception as e:
                logger.error(f"Error processing setup {setup_model.id}: {e}")
                db.session.rollback()
        
        return processed_count
        
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching unparsed messages: {e}")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error in parse_new_setup_messages: {e}")
        return 0
