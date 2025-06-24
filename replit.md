# A+ Trading Discord Bot Event-Driven Architecture

## Project Overview
Advanced Discord bot for processing A+ trading setups using event-driven architecture with PostgreSQL LISTEN/NOTIFY for robust inter-service communication.

## Recent Changes
- **2025-06-24**: Fortified Discord-to-Ingestion pipeline with vertical slice architecture alignment
  - Enforced proper event publishing boundaries (Discord bot uses only async event publishing)
  - Removed direct publisher fallback to maintain architectural integrity
  - Created event listener watchdog for automatic recovery
  - Built comprehensive test suite with valid/malformed/duplicate/delayed message scenarios
  - Added alert system for trading hours monitoring and stale processing detection
  - Implemented diagnostics with summary mode for dev/staging environments

## Project Architecture

### Event-Driven Pipeline
```
Discord Message → Bot.on_message() → PostgreSQL NOTIFY → Ingestion Listener → Database Storage
```

**Core Components:**
- **Discord Bot** (`features/discord_bot/bot.py`): Async event publishing via event bus
- **Event Publisher** (`common/events/publisher.py`): PostgreSQL NOTIFY with retry logic
- **Ingestion Listener** (`features/ingestion/listener.py`): PostgreSQL LISTEN consumer
- **Ingestion Service** (`features/ingestion/service.py`): Message processing and storage

### Key Architecture Principles
1. **Event Bus Only**: All cross-service communication uses PostgreSQL LISTEN/NOTIFY
2. **No Direct Database Access**: Services communicate through events, not direct DB calls
3. **Automatic Recovery**: Built-in failure detection and recovery mechanisms
4. **Flask Context Management**: Background threads properly handle Flask application context

## User Preferences

### Communication Style
- Professional and concise responses
- Focus on actionable solutions
- Avoid technical jargon when possible
- Provide clear status updates

### Code Style
- Comprehensive error handling with structured logging
- Event-driven architecture compliance
- Async/await patterns for all event operations
- Flask context safety for background operations

## Diagnostic Tools

### System Health Monitoring
- `diagnostics/full_pipeline_diagnostic.py`: Comprehensive pipeline health check with `--summary` mode
- `scripts/watchdog_listener.py`: Continuous monitoring and automatic listener restart
- `scripts/test_pipeline.py`: Comprehensive test suite for all message scenarios

### Alert System
- `features/ingestion/alerts.py`: Trading hours monitoring and stale processing detection
- Enhanced metrics endpoint includes alert notifications and counts
- Automatic logging of critical conditions (zero messages, listener down, processing delays)

## Critical System Requirements

### PostgreSQL LISTEN Connections
- Must maintain active `LISTEN "events"` connection
- Monitor via: `SELECT * FROM pg_stat_activity WHERE query = 'LISTEN "events"'`
- Auto-restart on connection drops

### Event Flow Validation
- Discord events must appear in events table within seconds
- Event/message ratio should be approximately 1:1
- Processing rate should exceed 90%

## Deployment Notes
- Event-driven architecture requires persistent PostgreSQL connections
- Ingestion listener auto-starts with Flask app
- Discord bot token and channel permissions verified working
- System automatically recovers from most failure modes

## Troubleshooting

### Common Issues
1. **No Recent Events**: Check PostgreSQL LISTEN connections, restart ingestion listener
2. **Event/Message Gap**: Verify ingestion service is processing events
3. **Processing Backlog**: Run event recovery system to clear stuck messages

### Recovery Commands
```bash
python scripts/watchdog_listener.py           # Continuous monitoring with auto-restart
python diagnostics/full_pipeline_diagnostic.py --summary  # Quick health check
python scripts/test_pipeline.py               # Comprehensive pipeline testing
```