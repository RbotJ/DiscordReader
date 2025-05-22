"""
Setup Data Provider

Provides access to setup data using PostgreSQL database.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

from common.db import db
from common.db_models import SetupModel
from common.events import publish_event, EventChannels

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def store_setup(setup_data: Dict[str, Any]) -> bool:
    """Store setup data in database"""
    try:
        setup = SetupModel(
            setup_id=setup_data.get('id'),
            ticker=setup_data.get('ticker'),
            timestamp=datetime.utcnow(),
            data=setup_data
        )
        db.session.add(setup)
        db.session.commit()

        # Publish setup event
        return publish_event(EventChannels.SETUP_CREATED, setup_data)
    except Exception as e:
        db.session.rollback()
        return False

def get_recent_setups(limit: int = 100) -> List[Dict[str, Any]]:
    """Get recent setups from database"""
    setups = SetupModel.query.order_by(
        SetupModel.timestamp.desc()
    ).limit(limit).all()
    return [setup.data for setup in setups]

def get_setup_by_id(setup_id: str) -> Optional[Dict[str, Any]]:
    """Get specific setup by ID"""
    setup = SetupModel.query.filter_by(setup_id=setup_id).first()
    return setup.data if setup else None
```

```python
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
import os
import json
from features.discord.message_parser import parse_message

from common.db import db
from common.db_models import SetupModel
from common.events import publish_event, EventChannels

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# File storage paths
DISCORD_MESSAGE_FILE = "latest_discord_message.json"
PARSED_SETUP_FILE = "parsed_setups.json"

def store_setup(setup_data: Dict[str, Any]) -> bool:
    """Store setup data in database"""
    try:
        setup = SetupModel(
            setup_id=setup_data.get('id'),
            ticker=setup_data.get('ticker'),
            timestamp=datetime.utcnow(),
            data=setup_data
        )
        db.session.add(setup)
        db.session.commit()

        # Publish setup event
        return publish_event(EventChannels.SETUP_CREATED, setup_data)
    except Exception as e:
        db.session.rollback()
        return False

def get_recent_setups(limit: int = 100) -> List[Dict[str, Any]]:
    """Get recent setups from database"""
    setups = SetupModel.query.order_by(
        SetupModel.timestamp.desc()
    ).limit(limit).all()
    return [setup.data for setup in setups]

def get_setup_by_id(setup_id: str) -> Optional[Dict[str, Any]]:
    """Get specific setup by ID"""
    setup = SetupModel.query.filter_by(setup_id=setup_id).first()
    return setup.data if setup else None

def get_latest_discord_message():
    """Get the latest Discord message from file if it exists."""
    try:
        if os.path.exists(DISCORD_MESSAGE_FILE):
            with open(DISCORD_MESSAGE_FILE, 'r') as f:
                return json.load(f)
        return None
    except Exception as e:
        logger.error(f"Error reading latest Discord message file: {e}")
        return None

def get_sample_setup():
    """Return a sample trading setup for demonstration purposes."""
    return {
        "datetime": datetime.now().isoformat(),
        "raw_message": """
A+ Trade Setups - Thursday May 20

$SPY Rejection Near 586
Bias: Bearish

$AAPL Breaking Support
Support at $182
Target: $178
Stop: $185

$NVDA Bounce at $920
Looks strong heading into earnings next week
        """,
        "tickers": ["SPY", "AAPL", "NVDA"],
        "primary_ticker": "SPY",
        "signal_type": "rejection",
        "bias": "bearish",
        "confidence": 0.95,
        "ticker_specific_data": {
            "SPY": {
                "signal_type": "rejection",
                "bias": "bearish",
                "detected_prices": [],
                "support_levels": [],
                "resistance_levels": [586],
                "target_levels": [],
                "stop_levels": [],
                "text_block": "$SPY Rejection Near 586\nBias: Bearish\n"
            },
            "AAPL": {
                "signal_type": "support",
                "bias": "bearish",
                "detected_prices": [],
                "support_levels": [182],
                "resistance_levels": [],
                "target_levels": [178],
                "stop_levels": [185],
                "text_block": "$AAPL Breaking Support\nSupport at $182\nTarget: $178\nStop: $185\n"
            },
            "NVDA": {
                "signal_type": "bounce",
                "bias": "bullish",
                "detected_prices": [920],
                "support_levels": [920],
                "resistance_levels": [],
                "target_levels": [],
                "stop_levels": [],
                "text_block": "$NVDA Bounce at $920\nLooks strong heading into earnings next week\n"
            }
        }
    }

def update_setup_from_discord():
    """
    Update the parsed setup data from the latest Discord message.
    Returns the parsed setup data.
    """
    # Get the latest Discord message
    discord_message = get_latest_discord_message()
    
    if not discord_message:
        logger.warning("No Discord message found. Using sample setup data.")
        setup_data = get_sample_setup()
    else:
        # Parse the Discord message
        message_content = discord_message.get('content')
        setup_data = parse_message(message_content)
        
        if not setup_data:
            logger.warning("Failed to parse Discord message. Using sample setup data.")
            setup_data = get_sample_setup()
        else:
            # Add metadata from Discord
            setup_data['discord_id'] = discord_message.get('id')
            setup_data['discord_author'] = discord_message.get('author')
            setup_data['discord_timestamp'] = discord_message.get('timestamp')
            setup_data['discord_channel'] = discord_message.get('channel_name')
    
    # Save the parsed setup data to file
    try:
        with open(PARSED_SETUP_FILE, 'w') as f:
            json.dump(setup_data, f, indent=2)
        logger.info(f"Parsed setup data saved to {PARSED_SETUP_FILE}")
    except Exception as e:
        logger.error(f"Error saving parsed setup data: {e}")
    
    return setup_data

def get_latest_setup():
    """
    Get the latest parsed setup data.
    If the file doesn't exist, create it first.
    """
    if not os.path.exists(PARSED_SETUP_FILE):
        return update_setup_from_discord()
    
    try:
        with open(PARSED_SETUP_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading parsed setup data: {e}")
        return get_sample_setup()

if __name__ == "__main__":
    # Test the module
    setup = get_latest_setup()
    print(f"Latest setup: {setup.get('primary_ticker')} - {setup.get('signal_type')}")
    print(f"Tickers: {', '.join(setup.get('tickers', []))}")
    print(f"Message:\n{setup.get('raw_message')}")
```

```python
"""
Setup Data Provider

Provides access to setup data using PostgreSQL database.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
import os
import json
from features.discord.message_parser import parse_message

from common.db import db
from common.db_models import SetupModel
from common.events import publish_event, EventChannels

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# File storage paths
DISCORD_MESSAGE_FILE = "latest_discord_message.json"
PARSED_SETUP_FILE = "parsed_setups.json"

def store_setup(setup_data: Dict[str, Any]) -> bool:
    """Store setup data in database"""
    try:
        setup = SetupModel(
            setup_id=setup_data.get('discord_id'),
            ticker=setup_data.get('primary_ticker'),
            timestamp=datetime.utcnow(),
            data=setup_data
        )
        db.session.add(setup)
        db.session.commit()

        # Publish setup event
        return publish_event(EventChannels.SETUP_CREATED, setup_data)
    except Exception as e:
        db.session.rollback()
        return False

def get_recent_setups(limit: int = 100) -> List[Dict[str, Any]]:
    """Get recent setups from database"""
    setups = SetupModel.query.order_by(
        SetupModel.timestamp.desc()
    ).limit(limit).all()
    return [setup.data for setup in setups]

def get_setup_by_id(setup_id: str) -> Optional[Dict[str, Any]]:
    """Get specific setup by ID"""
    setup = SetupModel.query.filter_by(setup_id=setup_id).first()
    return setup.data if setup else None

def get_latest_discord_message():
    """Get the latest Discord message from file if it exists."""
    try:
        if os.path.exists(DISCORD_MESSAGE_FILE):
            with open(DISCORD_MESSAGE_FILE, 'r') as f:
                return json.load(f)
        return None
    except Exception as e:
        logger.error(f"Error reading latest Discord message file: {e}")
        return None

def get_sample_setup():
    """Return a sample trading setup for demonstration purposes."""
    return {
        "datetime": datetime.now().isoformat(),
        "raw_message": """
A+ Trade Setups - Thursday May 20

$SPY Rejection Near 586
Bias: Bearish

$AAPL Breaking Support
Support at $182
Target: $178
Stop: $185

$NVDA Bounce at $920
Looks strong heading into earnings next week
        """,
        "tickers": ["SPY", "AAPL", "NVDA"],
        "primary_ticker": "SPY",
        "signal_type": "rejection",
        "bias": "bearish",
        "confidence": 0.95,
        "ticker_specific_data": {
            "SPY": {
                "signal_type": "rejection",
                "bias": "bearish",
                "detected_prices": [],
                "support_levels": [],
                "resistance_levels": [586],
                "target_levels": [],
                "stop_levels": [],
                "text_block": "$SPY Rejection Near 586\nBias: Bearish\n"
            },
            "AAPL": {
                "signal_type": "support",
                "bias": "bearish",
                "detected_prices": [],
                "support_levels": [182],
                "resistance_levels": [],
                "target_levels": [178],
                "stop_levels": [185],
                "text_block": "$AAPL Breaking Support\nSupport at $182\nTarget: $178\nStop: $185\n"
            },
            "NVDA": {
                "signal_type": "bounce",
                "bias": "bullish",
                "detected_prices": [920],
                "support_levels": [920],
                "resistance_levels": [],
                "target_levels": [],
                "stop_levels": [],
                "text_block": "$NVDA Bounce at $920\nLooks strong heading into earnings next week\n"
            }
        }
    }

def update_setup_from_discord():
    """
    Update the parsed setup data from the latest Discord message.
    Returns the parsed setup data.
    """
    # Get the latest Discord message
    discord_message = get_latest_discord_message()
    
    if not discord_message:
        logger.warning("No Discord message found. Using sample setup data.")
        setup_data = get_sample_setup()
    else:
        # Parse the Discord message
        message_content = discord_message.get('content')
        setup_data = parse_message(message_content)
        
        if not setup_data:
            logger.warning("Failed to parse Discord message. Using sample setup data.")
            setup_data = get_sample_setup()
        else:
            # Add metadata from Discord
            setup_data['discord_id'] = discord_message.get('id')
            setup_data['discord_author'] = discord_message.get('author')
            setup_data['discord_timestamp'] = discord_message.get('timestamp')
            setup_data['discord_channel'] = discord_message.get('channel_name')

            # Store setup data in database
            store_setup(setup_data)
    
    # Save the parsed setup data to file
    try:
        with open(PARSED_SETUP_FILE, 'w') as f:
            json.dump(setup_data, f, indent=2)
        logger.info(f"Parsed setup data saved to {PARSED_SETUP_FILE}")
    except Exception as e:
        logger.error(f"Error saving parsed setup data: {e}")
    
    return setup_data

def get_latest_setup():
    """
    Get the latest parsed setup data.
    If the file doesn't exist, create it first.
    """
    if not os.path.exists(PARSED_SETUP_FILE):
        return update_setup_from_discord()
    
    try:
        with open(PARSED_SETUP_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading parsed setup data: {e}")
        return get_sample_setup()

if __name__ == "__main__":
    # Test the module
    setup = get_latest_setup()
    print(f"Latest setup: {setup.get('primary_ticker')} - {setup.get('signal_type')}")
    print(f"Tickers: {', '.join(setup.get('tickers', []))}")
    print(f"Message:\n{setup.get('raw_message')}")
```

```python
"""
Setup Data Provider

Provides access to setup data using PostgreSQL database.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
import os
import json
from features.discord.message_parser import parse_message

from common.db import db
from common.db_models import SetupModel
from common.events import publish_event, EventChannels

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# File storage paths
DISCORD_MESSAGE_FILE = "latest_discord_message.json"
PARSED_SETUP_FILE = "parsed_setups.json"

def store_setup(setup_data: Dict[str, Any]) -> bool:
    """Store setup data in database"""
    try:
        setup = SetupModel(
            setup_id=setup_data.get('discord_id'),
            ticker=setup_data.get('primary_ticker'),
            timestamp=datetime.utcnow(),
            data=setup_data
        )
        db.session.add(setup)
        db.session.commit()

        # Publish setup event
        return publish_event(EventChannels.SETUP_CREATED, setup_data)
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error storing setup data: {e}")
        return False

def get_recent_setups(limit: int = 100) -> List[Dict[str, Any]]:
    """Get recent setups from database"""
    setups = SetupModel.query.order_by(
        SetupModel.timestamp.desc()
    ).limit(limit).all()
    return [setup.data for setup in setups]

def get_setup_by_id(setup_id: str) -> Optional[Dict[str, Any]]:
    """Get specific setup by ID"""
    setup = SetupModel.query.filter_by(setup_id=setup_id).first()
    return setup.data if setup else None

def get_latest_discord_message():
    """Get the latest Discord message from file if it exists."""
    try:
        if os.path.exists(DISCORD_MESSAGE_FILE):
            with open(DISCORD_MESSAGE_FILE, 'r') as f:
                return json.load(f)
        return None
    except Exception as e:
        logger.error(f"Error reading latest Discord message file: {e}")
        return None

def get_sample_setup():
    """Return a sample trading setup for demonstration purposes."""
    return {
        "datetime": datetime.now().isoformat(),
        "raw_message": """
A+ Trade Setups - Thursday May 20

$SPY Rejection Near 586
Bias: Bearish

$AAPL Breaking Support
Support at $182
Target: $178
Stop: $185

$NVDA Bounce at $920
Looks strong heading into earnings next week
        """,
        "tickers": ["SPY", "AAPL", "NVDA"],
        "primary_ticker": "SPY",
        "signal_type": "rejection",
        "bias": "bearish",
        "confidence": 0.95,
        "ticker_specific_data": {
            "SPY": {
                "signal_type": "rejection",
                "bias": "bearish",
                "detected_prices": [],
                "support_levels": [],
                "resistance_levels": [586],
                "target_levels": [],
                "stop_levels": [],
                "text_block": "$SPY Rejection Near 586\nBias: Bearish\n"
            },
            "AAPL": {
                "signal_type": "support",
                "bias": "bearish",
                "detected_prices": [],
                "support_levels": [182],
                "resistance_levels": [],
                "target_levels": [178],
                "stop_levels": [185],
                "text_block": "$AAPL Breaking Support\nSupport at $182\nTarget: $178\nStop: $185\n"
            },
            "NVDA": {
                "signal_type": "bounce",
                "bias": "bullish",
                "detected_prices": [920],
                "support_levels": [920],
                "resistance_levels": [],
                "target_levels": [],
                "stop_levels": [],
                "text_block": "$NVDA Bounce at $920\nLooks strong heading into earnings next week\n"
            }
        }
    }

def update_setup_from_discord():
    """
    Update the parsed setup data from the latest Discord message.
    Returns the parsed setup data.
    """
    # Get the latest Discord message
    discord_message = get_latest_discord_message()
    
    if not discord_message:
        logger.warning("No Discord message found. Using sample setup data.")
        setup_data = get_sample_setup()
    else:
        # Parse the Discord message
        message_content = discord_message.get('content')
        setup_data = parse_message(message_content)
        
        if not setup_data:
            logger.warning("Failed to parse Discord message. Using sample setup data.")
            setup_data = get_sample_setup()
        else:
            # Add metadata from Discord
            setup_data['discord_id'] = discord_message.get('id')
            setup_data['discord_author'] = discord_message.get('author')
            setup_data['discord_timestamp'] = discord_message.get('timestamp')
            setup_data['discord_channel'] = discord_message.get('channel_name')

            # Store setup data in database
            store_setup(setup_data)
    
    # Save the parsed setup data to file
    try:
        with open(PARSED_SETUP_FILE, 'w') as f:
            json.dump(setup_data, f, indent=2)
        logger.info(f"Parsed setup data saved to {PARSED_SETUP_FILE}")
    except Exception as e:
        logger.error(f"Error saving parsed setup data: {e}")
    
    return setup_data

def get_latest_setup():
    """
    Get the latest parsed setup data.
    If the file doesn't exist, create it first.
    """
    # First try to get from the db
    recent_setups = get_recent_setups(limit=1)
    if recent_setups:
        return recent_setups[0]

    # If not in db, fall back to the file
    if not os.path.exists(PARSED_SETUP_FILE):
        return update_setup_from_discord()
    
    try:
        with open(PARSED_SETUP_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading parsed setup data: {e}")
        return get_sample_setup()

if __name__ == "__main__":
    # Test the module
    setup = get_latest_setup()
    print(f"Latest setup: {setup.get('primary_ticker')} - {setup.get('signal_type')}")
    print(f"Tickers: {', '.join(setup.get('tickers', []))}")
    print(f"Message:\n{setup.get('raw_message')}")