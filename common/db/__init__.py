"""
Database Management Package

Centralized database management for the trading application.
Provides organized access to database utilities, session management, and base models.
"""

from .session import db, initialize_db
from .utils import execute_query, check_database_connection, get_latest_events
from .base import BaseModel

# Import publish_event from the main common.db module
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from common.db import publish_event

# Re-export commonly used components
__all__ = [
    'db',
    'initialize_db', 
    'execute_query',
    'check_database_connection',
    'get_latest_events',
    'BaseModel',
    'publish_event'
]