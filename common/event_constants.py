"""
Event Constants Module

This module defines constants for event channels and types used in Redis pub/sub.
"""

# Setup event channels
SETUP_CREATED_CHANNEL = "events:setup:created"
SETUP_UPDATED_CHANNEL = "events:setup:updated"
SIGNAL_CREATED_CHANNEL = "events:signal:created"
SIGNAL_TRIGGERED_CHANNEL = "events:signal:triggered"
BIAS_CREATED_CHANNEL = "events:bias:created"
BIAS_FLIPPED_CHANNEL = "events:bias:flipped"

# Discord message channels
DISCORD_RAW_MESSAGE_CHANNEL = "events:discord:raw_messages"
DISCORD_SETUP_MESSAGE_CHANNEL = "events:discord:setup_messages"

# Event types
class EventType:
    # Setup events
    SETUP_CREATED = "setup.created"
    SETUP_UPDATED = "setup.updated"
    SIGNAL_CREATED = "signal.created"
    SIGNAL_TRIGGERED = "signal.triggered"
    BIAS_CREATED = "bias.created"
    BIAS_FLIPPED = "bias.flipped"
    
    # Discord events
    DISCORD_MESSAGE_RECEIVED = "discord.message.received"
    DISCORD_SETUP_MESSAGE_RECEIVED = "discord.setup_message.received"