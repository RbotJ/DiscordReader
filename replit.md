# A+ Trading Discord Bot Event-Driven Architecture

## Project Overview
Advanced Discord bot for processing A+ trading setups using event-driven architecture with PostgreSQL LISTEN/NOTIFY for robust inter-service communication.

## Recent Changes
- **2025-06-24**: Restored event-driven architecture with comprehensive failure detection and recovery
  - Fixed PostgreSQL LISTEN connection drops
  - Implemented automatic ingestion listener restart capability
  - Added comprehensive diagnostic tools for system health monitoring
  - Enhanced error handling with retry logic and fallback mechanisms

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
- `event_system_diagnostic.py`: Direct database analysis without Flask overhead
- `full_pipeline_diagnostic.py`: Comprehensive pipeline health check
- `restart_ingestion_listener.py`: Automatic listener recovery

### Event Publishing Failure Detection
- `audit_event_publishing_system.py`: In-depth failure analysis
- `event_recovery_system.py`: Automatic recovery for orphaned events
- Built-in instrumentation for real-time monitoring

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
python restart_ingestion_listener.py  # Restore PostgreSQL LISTEN
python event_recovery_system.py       # Fix orphaned events
python full_pipeline_diagnostic.py    # Comprehensive health check
```