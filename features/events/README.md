# Events Feature - Enhanced PostgreSQL Event Bus

The Events feature provides a sophisticated event system with correlation tracking, enabling complete operational visibility across the trading platform.

## Overview

This feature implements a production-grade event bus using PostgreSQL with JSONB storage, correlation tracking, and automated cleanup. It replaces simple logging with structured event publishing that enables end-to-end flow tracing.

## Key Components

### Enhanced Publisher (`enhanced_publisher.py`)
- **EventPublisher class**: Core event publishing with correlation tracking
- **Automatic correlation ID generation**: Links related events across time
- **Structured event publishing**: Consistent data format and metadata
- **Error handling**: Robust error logging and transaction rollback

### Query Service (`query_service.py`)
- **Event filtering**: By channel, type, source, and time ranges
- **Correlation flow tracing**: Find all events with same correlation ID
- **Advanced search**: JSONB payload searching with GIN indexes
- **Event statistics**: Operational health metrics and analytics
- **Automated cleanup**: 90-day retention policy enforcement

### Cleanup Service (`cleanup_service.py`)
- **Scheduled maintenance**: Daily cleanup at 2 AM
- **Background processing**: Non-blocking cleanup operations
- **Event logging**: Cleanup operations logged as system events
- **Manual triggers**: Force cleanup for testing or maintenance

## Database Schema

### Events Table
```sql
CREATE TABLE events (
  id SERIAL PRIMARY KEY,
  channel VARCHAR(50) NOT NULL,                  -- e.g. 'setup:created'
  event_type VARCHAR(100) NOT NULL,              -- e.g. 'signal.triggered'
  source VARCHAR(100),                           -- e.g. 'discord_parser'
  correlation_id UUID,                           -- for tracing flows
  data JSONB NOT NULL,                           -- structured payload
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
```

### Indexes for Performance
- **Channel index**: Fast filtering by event channel
- **Type index**: Quick event type queries
- **Source index**: Filter by service/module source
- **Correlation index**: Efficient correlation flow tracing
- **Time index**: Time-based range queries
- **GIN index**: JSONB payload searching

## Event Channels

### Operational Channels
- `discord:message` - Discord message events
- `ingestion:message` - Message ingestion processing
- `parsing:setup` - Setup parsing and extraction
- `bot:startup` - Discord bot lifecycle events
- `system` - System-level events and errors

### Trading Channels  
- `setup:created` - New trading setup events
- `alert:price` - Price alert triggers
- `ticker:data` - Real-time market data events

## Event Types

### Discord Events
- `discord.message.received` - Message received from Discord
- `discord.message.processed` - Message processing completed
- `bot.connected` - Bot connection established
- `channel.scanned` - Channel discovery completed

### Processing Events
- `ingestion.message.stored` - Message stored in database
- `parsing.setup.parsed` - Setup successfully parsed
- `setup.created` - New setup created from parsing

### System Events
- `system.error` - Error conditions
- `system.warning` - Warning conditions
- `system.info` - Informational events

## Correlation Tracking

Events are linked using UUID correlation IDs to trace complete flows:

```
Discord Message (correlation_id: abc-123)
    ↓
Ingestion Started (correlation_id: abc-123)
    ↓  
Parsing Completed (correlation_id: abc-123)
    ↓
Setup Created (correlation_id: abc-123)
```

## Usage Examples

### Publishing Events
```python
from features.events.enhanced_publisher import EventPublisher

# Publish with automatic correlation ID
event = EventPublisher.publish_event(
    channel='setup:created',
    event_type='setup.parsed',
    data={'ticker': 'AAPL', 'price': 150.25},
    source='discord_parser'
)

# Publish with specific correlation ID
event = EventPublisher.publish_setup_parsed(
    setup_data={'ticker': 'TSLA', 'confidence': 0.85},
    correlation_id='existing-correlation-id'
)
```

### Querying Events
```python
from features.events.query_service import EventQueryService

# Get recent events by channel
events = EventQueryService.get_events_by_channel(
    'discord:message', 
    since=datetime.now() - timedelta(hours=24)
)

# Trace correlation flow
flow = EventQueryService.get_events_by_correlation('abc-123-def-456')

# Get operational statistics
stats = EventQueryService.get_event_statistics(
    since=datetime.now() - timedelta(hours=24)
)
```

### Using Common Interface
```python
from common.db import publish_event

# Simple event publishing
success = publish_event(
    event_type='setup.parsed',
    payload={'ticker': 'AAPL'},
    channel='setup:created',
    source='parser_service'
)
```

## Integration Points

### Dashboard Integration
- Event analytics API endpoints at `/dashboard/events`
- Real-time operational health monitoring
- Interactive correlation flow tracing
- Live event filtering and search

### Discord Bot Integration
- Automatic correlation ID generation for message flows
- Complete ingestion pipeline event tracking
- Startup and real-time operation monitoring

### Cleanup Integration
- Automatic startup of cleanup scheduler in main.py
- Background thread management with Flask lifecycle
- Event publishing for cleanup operations

## Monitoring & Maintenance

### Health Monitoring
```sql
-- Recent event volume by channel
SELECT channel, COUNT(*) 
FROM events 
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY channel;

-- Correlation flow completion rates
SELECT 
    COUNT(DISTINCT correlation_id) as total_flows,
    COUNT(DISTINCT CASE WHEN event_type = 'setup.created' 
                        THEN correlation_id END) as completed_flows
FROM events 
WHERE correlation_id IS NOT NULL;
```

### Performance Optimization
- GIN indexes on JSONB data for fast payload searches
- Regular VACUUM and ANALYZE on events table
- Automatic cleanup prevents unbounded table growth
- Connection pooling for high-throughput scenarios

## Error Handling

### Event Publishing Failures
- Automatic transaction rollback on errors
- Detailed error logging with context
- Graceful degradation (application continues on event failures)
- Retry logic for transient database issues

### Cleanup Service Failures
- Error events published for failed cleanups
- Automatic retry on next scheduled run
- Manual cleanup triggers for recovery
- Monitoring alerts for cleanup failures

---

*Last updated: 2025-05-28*
*Feature status: Production ready with complete correlation tracking*