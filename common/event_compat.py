    """
    Event System (PostgreSQL-based)

    Simplified event publishing for audit/logging purposes only.
    No subscription or callback logic is retained.
    """

    import logging
    from typing import Dict, Any, List, Optional
    from datetime import datetime

    from common.db import db
    from common.models_db import EventModel

    logger = logging.getLogger(__name__)

    def publish_event(channel: str, data: Dict[str, Any]) -> bool:
        """Publish an event to the PostgreSQL event log."""
        try:
            event = EventModel(
                channel=channel,
                data=data,
                created_at=datetime.utcnow()
            )
            with db.session.begin():
                db.session.add(event)
            logger.debug(f"Published event to channel '{channel}'")
            return True
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return False

    def get_latest_events(channel: str, since_timestamp: Optional[datetime] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Query the latest events for a given channel."""
        try:
            query = db.session.query(EventModel).filter(
                EventModel.channel == channel
            )
            if since_timestamp:
                query = query.filter(EventModel.created_at > since_timestamp)

            events = query.order_by(EventModel.created_at.desc()).limit(limit).all()
            return [
                {
                    'id': e.id,
                    'channel': e.channel,
                    'data': e.data,
                    'created_at': e.created_at
                } for e in events
            ]
        except Exception as e:
            logger.error(f"Failed to get latest events: {e}")
            return []
