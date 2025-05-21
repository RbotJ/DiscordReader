try:
    # Poll for new events from PostgreSQL event bus
    events = poll_events([DISCORD_SETUP_MESSAGE_CHANNEL], self.last_event_id)

    # Process any new events
    for event in events:
        try:
            if '_event_id' in event:
                self._process_event(event)
                self.last_event_id = max(self.last_event_id, event['_event_id'])
        except Exception as e:
            logger.error(f"Error processing event: {e}")

    # Sleep briefly to avoid excessive database queries  
    time.sleep(0.5)
except Exception as e:
    logger.error(f"Error polling or processing events: {e}")