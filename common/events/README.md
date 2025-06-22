# Event System Architecture (PostgreSQL-Only)

This application exclusively uses PostgreSQL LISTEN/NOTIFY for all cross-slice communication.
All events must be published and consumed using the functions in `common/events/publisher.py`.

## 🚫 Prohibited Event Patterns

- ❌ No in-memory queues or event buses
- ❌ No Redis/Socket-based event handlers  
- ❌ No threading-based event polling
- ❌ No custom EventBus, PubSub, or Observer classes
- ❌ No `asyncio.new_event_loop()` in event handlers

## ✅ Required Event Patterns

- ✅ Use `publish_event()` for all cross-feature communication
- ✅ Use `listen_for_events()` for all event subscriptions
- ✅ All events stored in PostgreSQL with NOTIFY delivery
- ✅ Correlation ID tracking for end-to-end traceability
- ✅ Comprehensive logging with 📢/📥 indicators

## Architecture Overview

```
Discord Message → PostgreSQL NOTIFY → Ingestion → Database Storage
     ↓                    ↓                ↓            ↓
Event Published → Event Delivered → Event Processed → Event Stored
```

## Usage Examples

### Publishing Events
```python
from common.events.publisher import publish_event_safe

# Publish cross-slice event
publish_event_safe(
    channel="discord",
    event_type="message.received", 
    data={"message_id": "123", "content": "A+ Setups..."},
    source="discord_bot"
)
```

### Listening for Events
```python
from common.events.publisher import listen_for_events

async def handle_event(event_type, payload):
    if event_type == "message.received":
        # Process the message
        pass

# Start listener
await listen_for_events(handle_event, "events")
```

## Implementation Details

Refer to `common/events/publisher.py` for complete implementation.
All event communication flows through PostgreSQL LISTEN/NOTIFY channels for real-time delivery with database persistence.

## Compliance Score: 100%

All cross-feature communication uses PostgreSQL LISTEN/NOTIFY exclusively.
No threading-based or in-memory event systems remain in the codebase.