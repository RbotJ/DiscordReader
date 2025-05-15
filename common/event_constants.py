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

# Event types
class EventType:
    SETUP_CREATED = "setup.created"
    SETUP_UPDATED = "setup.updated"
    SIGNAL_CREATED = "signal.created"
    SIGNAL_TRIGGERED = "signal.triggered"
    BIAS_CREATED = "bias.created"
    BIAS_FLIPPED = "bias.flipped"