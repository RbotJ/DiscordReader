"""
PostgreSQL-based Event and Cache System

This module provides a database-backed event system and caching mechanism that replaces
Redis pub/sub and Redis caching for feature-to-feature communication.
"""
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from common.db import db
from common.event_constants import EventChannels

logger = logging.getLogger(__name__)

class EventModel(db.Model):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True)
    channel = Column(String(255), nullable=False)
    data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class CacheModel(db.Model):
    __tablename__ = 'cache'

    key = Column(String(255), primary_key=True)
    value = Column(JSON)
    expires_at = Column(DateTime)

def publish_event(channel: str, data: Dict[str, Any]) -> bool:
    """Publish an event to a channel using PostgreSQL."""
    try:
        event = EventModel(
            channel=channel,
            data=data,
            created_at=datetime.utcnow()
        )
        db.session.add(event)
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")
        db.session.rollback()
        return False

def get_latest_events(channel: str, since_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get latest events from a channel."""
    try:
        query = EventModel.query.filter_by(channel=channel)
        if since_id:
            query = query.filter(EventModel.id > since_id)
        events = query.order_by(EventModel.id.desc()).limit(100).all()
        return [{"id": e.id, "channel": e.channel, "data": e.data} for e in events]
    except Exception as e:
        logger.error(f"Failed to get events: {e}")
        return []

def cache_data(key: str, value: Any, expiry_seconds: int = 300) -> bool:
    """Cache data using PostgreSQL."""
    try:
        expires_at = datetime.utcnow() + timedelta(seconds=expiry_seconds)
        cache_entry = CacheModel.query.get(key)

        if cache_entry:
            cache_entry.value = value
            cache_entry.expires_at = expires_at
        else:
            cache_entry = CacheModel(key=key, value=value, expires_at=expires_at)
            db.session.add(cache_entry)

        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to cache data: {e}")
        db.session.rollback()
        return False

def get_from_cache(key: str) -> Optional[Any]:
    """Get data from cache."""
    try:
        cache_entry = CacheModel.query.get(key)
        if cache_entry and cache_entry.expires_at > datetime.utcnow():
            return cache_entry.value
        return None
    except Exception as e:
        logger.error(f"Failed to get cached data: {e}")
        return None

def clear_expired_cache() -> None:
    """Clear expired cache entries."""
    try:
        CacheModel.query.filter(CacheModel.expires_at < datetime.utcnow()).delete()
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to clear expired cache: {e}")
        db.session.rollback()