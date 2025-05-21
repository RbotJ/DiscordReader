from common.events import poll_events, publish_event
from common.event_constants import DISCORD_MESSAGE_CHANNEL
from common.event_compat import event_client

# Configure logger 
logger = logging.getLogger(__name__)

class MessageConsumer:
    def __init__(self):
        self.running = True
        self.last_event_id = 0

    def start(self):
        """Start polling for Discord messages."""
        try:
            logger.info("Starting Discord message consumer")

            # Main polling loop
            while self.running:
                try:
                    # Poll for new events on the Discord message channel using PostgreSQL
                    events = poll_events([DISCORD_MESSAGE_CHANNEL], self.last_event_id)

                    # Process any new events
                    for event in events:
                        self._process_event(event)
                        self.last_event_id = max(self.last_event_id, event['id'])

                    time.sleep(0.5)

                except Exception as e:
                    logger.error(f"Error polling events: {e}")
                    time.sleep(2)

        except Exception as e:
            logger.error(f"Error in message consumer: {e}")
        finally:
            logger.info("Discord message consumer stopped")