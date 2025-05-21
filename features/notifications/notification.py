
"""
Notification service using PostgreSQL for event storage.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from common.db import db
from common.db_models import NotificationModel 
from common.events import publish_event, EventChannels

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.logger = logger

    def send_notification(self, notification_type: str, data: Dict[str, Any]) -> bool:
        """Send a notification by storing in DB and publishing event."""
        try:
            # Store notification in database
            notification = NotificationModel(
                type=notification_type,
                message=str(data),
                meta_data=data,
                created_at=datetime.utcnow()
            )
            db.session.add(notification)
            db.session.commit()

            # Publish notification event
            publish_event(EventChannels.NOTIFICATIONS, {
                'type': notification_type,
                'data': data,
                'timestamp': datetime.utcnow().isoformat()
            })
            return True

        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")
            db.session.rollback()
            return False

    def get_recent_notifications(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent notifications from database."""
        try:
            notifications = NotificationModel.query\
                .order_by(NotificationModel.created_at.desc())\
                .limit(limit)\
                .all()
            
            return [n.to_dict() for n in notifications]
        except Exception as e:
            self.logger.error(f"Failed to get notifications: {e}")
            return []
