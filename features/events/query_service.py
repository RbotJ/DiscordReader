"""
Event Query Service

Provides structured querying interface for the enhanced event system.
Supports filtering by channel, type, time, and correlation tracking.
"""
import uuid
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import desc, and_, or_

from features.events.models import Event
from common.db import db

logger = logging.getLogger(__name__)


class EventQueryService:
    """Service for querying events with advanced filtering capabilities."""
    
    @staticmethod
    def get_events_by_channel(
        channel: str, 
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Event]:
        """
        Get events filtered by channel with optional time filtering.
        
        Args:
            channel: Event channel to filter by
            since: Optional datetime to filter events after
            limit: Maximum number of events to return
            
        Returns:
            List[Event]: Filtered events in descending chronological order
        """
        try:
            query = Event.query.filter_by(channel=channel)
            
            if since:
                query = query.filter(Event.created_at >= since)
            
            return query.order_by(desc(Event.created_at)).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error querying events by channel {channel}: {e}")
            return []
    
    @staticmethod
    def get_events_by_type(
        event_type: str,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Event]:
        """
        Get events filtered by event type with optional time filtering.
        
        Args:
            event_type: Event type to filter by
            since: Optional datetime to filter events after
            limit: Maximum number of events to return
            
        Returns:
            List[Event]: Filtered events in descending chronological order
        """
        try:
            query = Event.query.filter_by(event_type=event_type)
            
            if since:
                query = query.filter(Event.created_at >= since)
            
            return query.order_by(desc(Event.created_at)).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error querying events by type {event_type}: {e}")
            return []
    
    @staticmethod
    def get_events_by_source(
        source: str,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Event]:
        """
        Get events filtered by source with optional time filtering.
        
        Args:
            source: Event source to filter by
            since: Optional datetime to filter events after
            limit: Maximum number of events to return
            
        Returns:
            List[Event]: Filtered events in descending chronological order
        """
        try:
            query = Event.query.filter_by(source=source)
            
            if since:
                query = query.filter(Event.created_at >= since)
            
            return query.order_by(desc(Event.created_at)).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error querying events by source {source}: {e}")
            return []
    
    @staticmethod
    def get_events_by_correlation(correlation_id: str) -> List[Event]:
        """
        Get all events with the same correlation ID for flow tracing.
        
        Args:
            correlation_id: Correlation UUID to search for
            
        Returns:
            List[Event]: Related events in chronological order
        """
        try:
            uuid_obj = uuid.UUID(correlation_id)
            return Event.query.filter_by(
                correlation_id=uuid_obj
            ).order_by(Event.created_at.asc()).all()
            
        except (ValueError, Exception) as e:
            logger.error(f"Error querying events by correlation {correlation_id}: {e}")
            return []
    
    @staticmethod
    def get_recent_events(
        hours: int = 24,
        channels: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Event]:
        """
        Get recent events within specified time window.
        
        Args:
            hours: Number of hours to look back
            channels: Optional list of channels to filter by
            limit: Maximum number of events to return
            
        Returns:
            List[Event]: Recent events in descending chronological order
        """
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            query = Event.query.filter(Event.created_at >= since)
            
            if channels:
                query = query.filter(Event.channel.in_(channels))
            
            return query.order_by(desc(Event.created_at)).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error querying recent events: {e}")
            return []
    
    @staticmethod
    def search_events_by_data(
        search_criteria: Dict[str, Any],
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Event]:
        """
        Search events by data payload content using JSONB operations.
        
        Args:
            search_criteria: Dict of key-value pairs to search in event data
            since: Optional datetime to filter events after
            limit: Maximum number of events to return
            
        Returns:
            List[Event]: Matching events in descending chronological order
        """
        try:
            query = Event.query
            
            # Add JSONB containment filters
            for key, value in search_criteria.items():
                query = query.filter(Event.data[key].astext == str(value))
            
            if since:
                query = query.filter(Event.created_at >= since)
            
            return query.order_by(desc(Event.created_at)).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error searching events by data: {e}")
            return []
    
    @staticmethod
    def get_event_statistics(
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get event statistics for monitoring and analytics.
        
        Args:
            since: Optional datetime to calculate stats from
            
        Returns:
            Dict: Event statistics including counts by channel, type, source
        """
        try:
            query = Event.query
            if since:
                query = query.filter(Event.created_at >= since)
            
            events = query.all()
            
            # Calculate statistics
            stats = {
                'total_events': len(events),
                'channels': {},
                'event_types': {},
                'sources': {},
                'timespan': {
                    'since': since.isoformat() if since else None,
                    'until': datetime.utcnow().isoformat()
                }
            }
            
            for event in events:
                # Count by channel
                stats['channels'][event.channel] = stats['channels'].get(event.channel, 0) + 1
                
                # Count by event type
                stats['event_types'][event.event_type] = stats['event_types'].get(event.event_type, 0) + 1
                
                # Count by source
                if event.source:
                    stats['sources'][event.source] = stats['sources'].get(event.source, 0) + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating event statistics: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def cleanup_old_events() -> int:
        """
        Clean up events older than 90 days per retention policy.
        
        Returns:
            int: Number of events deleted
        """
        try:
            result = db.session.execute("SELECT cleanup_old_events()")
            deleted_count = result.scalar()
            db.session.commit()
            
            logger.info(f"Cleaned up {deleted_count} old events")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error during event cleanup: {e}")
            db.session.rollback()
            return 0