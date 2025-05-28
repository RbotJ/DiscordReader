# Discord Bot Feature - Real-time Message Monitoring

The Discord Bot feature provides real-time message monitoring, channel scanning, and ingestion pipeline integration with complete correlation tracking.

## Overview

This feature implements a Discord bot that automatically monitors trading channels, detects new messages, and triggers the ingestion pipeline with full correlation tracking for operational visibility.

## Key Components

### Discord Bot (`bot.py`)
- **TradingDiscordBot class**: Main Discord client with real-time monitoring
- **Channel scanning**: Automatic discovery of #aplus-setups channels
- **Startup catch-up**: Process messages since last recorded timestamp
- **Real-time triggers**: Immediate ingestion on new messages
- **Correlation tracking**: End-to-end flow visibility

### Configuration (`config/settings.py`)
- **Environment validation**: Discord token and configuration checks
- **Channel management**: Guild and channel ID handling
- **Security**: Token validation and secure storage

### Services

#### Correlation Service (`services/correlation_service.py`)
- **Flow tracking**: Generate correlation IDs for complete message journeys
- **Event publishing**: Structured events at each processing stage
- **Flow analysis**: Retrieve complete correlation flows for debugging

#### Channel Monitor (`services/channel_monitor.py`)
- **Channel discovery**: Scan guilds for trading channels
- **Database updates**: Maintain channel information in discord_channels table
- **Monitoring status**: Track which channels are being monitored

#### Message Relay (`services/message_relay.py`)
- **Ingestion integration**: Direct calls to ingestion service
- **Dependency injection**: Receive ingestion service via constructor
- **Error handling**: Robust error management with event logging

## Database Integration

### Discord Channels Table
```sql
CREATE TABLE discord_channels (
  id SERIAL PRIMARY KEY,
  channel_id VARCHAR(255) UNIQUE NOT NULL,
  channel_name VARCHAR(255),
  guild_id VARCHAR(255),
  is_monitored BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Discord Messages Table
```sql
CREATE TABLE discord_messages (
  id SERIAL PRIMARY KEY,
  message_id VARCHAR(255) UNIQUE NOT NULL,
  channel_id VARCHAR(255) NOT NULL,
  author_id VARCHAR(255),
  content TEXT,
  timestamp TIMESTAMP WITH TIME ZONE,
  processed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Event Publishing

### Message Flow Events
The bot publishes events at each stage of message processing:

1. **Message Received**: `discord.message.received`
2. **Ingestion Started**: `ingestion.catchup.started`
3. **Ingestion Completed**: `ingestion.catchup.completed`
4. **Processing Results**: Success/failure with detailed metadata

### Event Channels
- `discord:message` - Message-related events
- `ingestion:batch` - Batch processing events
- `bot:startup` - Bot lifecycle events
- `system` - Error and system events

## Correlation Tracking

Every message flow gets a unique correlation ID that links all related events:

```
Discord Message Received → correlation_id: abc-123
    ↓
Ingestion Started → correlation_id: abc-123  
    ↓
Message Stored → correlation_id: abc-123
    ↓
Parsing Completed → correlation_id: abc-123
    ↓
Setup Created → correlation_id: abc-123
```

## Configuration

### Environment Variables
```bash
# Required
DISCORD_BOT_TOKEN=your_bot_token_here

# Optional (auto-detected if not provided)
DISCORD_GUILD_ID=your_guild_id
DISCORD_CHANNEL_ID=your_channel_id
```

### Bot Permissions
Required Discord bot permissions:
- **Read Messages**: View channel content
- **Read Message History**: Access historical messages
- **Use Slash Commands**: Future command support

## Usage Examples

### Manual Bot Management
```python
from features.discord_bot.bot import get_global_client_manager

# Start bot
manager = get_global_client_manager()
if manager:
    success = await manager.start_bot()
    print(f"Bot started: {success}")

# Check bot status
if manager and manager.bot:
    ready = manager.bot.is_ready()
    print(f"Bot ready: {ready}")
```

### Correlation Flow Tracing
```python
from features.discord_bot.services.correlation_service import DiscordCorrelationService

# Get complete flow for a correlation ID
flow = DiscordCorrelationService.get_message_correlation_flow('abc-123-def-456')
print(f"Flow status: {flow['status']}")
print(f"Completed stages: {flow['completed_stages']}")
```

## Integration Points

### Ingestion Service Integration
- **Direct service calls**: Bot calls ingestion service methods directly
- **Dependency injection**: Ingestion service provided via constructor
- **Error isolation**: Ingestion failures don't crash the bot

### Dashboard Integration
- **Real-time status**: Bot status displayed in operational dashboard
- **Event monitoring**: All bot events visible in event analytics
- **Correlation flows**: Complete message-to-setup journeys tracked

### Event System Integration
- **Structured publishing**: All events follow enhanced event schema
- **Correlation linking**: Related events connected via correlation IDs
- **Health monitoring**: Bot health tracked through event patterns

## Bot Lifecycle

### Startup Sequence
1. **Environment validation**: Check required Discord credentials
2. **Channel scanning**: Discover and catalog available channels
3. **Database updates**: Update discord_channels table
4. **Catch-up ingestion**: Process messages since last recorded timestamp
5. **Real-time monitoring**: Begin monitoring for new messages

### Runtime Operations
- **Message detection**: Immediate response to new messages in monitored channels
- **Ingestion triggers**: Automatic ingestion of new message batches
- **Error handling**: Graceful error recovery with event logging
- **Health monitoring**: Regular status checks and reporting

### Shutdown Sequence
- **Graceful disconnect**: Clean Discord connection closure
- **Final events**: Publish bot shutdown events
- **Service cleanup**: Clean up background services and threads

## Error Handling

### Connection Failures
- **Retry logic**: Automatic reconnection on network issues
- **Event logging**: Connection failures logged as system events
- **Graceful degradation**: Application continues without bot if needed

### Ingestion Failures
- **Error isolation**: Ingestion failures don't affect bot operation
- **Error events**: Failed ingestions logged with correlation tracking
- **Recovery**: Automatic retry on next message or manual trigger

### Configuration Issues
- **Validation**: Environment variables validated on startup
- **Clear messaging**: Detailed error messages for configuration problems
- **Fallback behavior**: Bot disabled if configuration incomplete

## Monitoring & Debugging

### Bot Health Checks
```python
# Check if bot is connected and ready
if manager and manager.bot:
    connected = manager.bot.is_ready()
    channel_id = manager.bot.aplus_setups_channel_id
    print(f"Bot connected: {connected}, Monitoring: {channel_id}")
```

### Event Analysis
```sql
-- Recent bot events
SELECT event_type, source, data, created_at 
FROM events 
WHERE source = 'discord_bot' 
ORDER BY created_at DESC 
LIMIT 10;

-- Correlation flow completion
SELECT 
    correlation_id,
    COUNT(*) as event_count,
    MAX(created_at) as last_event
FROM events 
WHERE correlation_id IS NOT NULL
GROUP BY correlation_id
ORDER BY last_event DESC;
```

### Performance Monitoring
- **Message processing time**: Track time from message to setup creation
- **Ingestion success rates**: Monitor successful vs failed ingestions
- **Channel activity**: Track message volume by channel
- **Bot uptime**: Monitor connection stability and uptime

## Security Considerations

### Token Management
- **Environment variables**: Tokens stored securely in environment
- **No hardcoding**: Never commit tokens to version control
- **Validation**: Token format and permissions validated on startup

### Permission Principle
- **Minimal permissions**: Bot requests only necessary Discord permissions
- **Read-only access**: Bot does not send messages or modify Discord content
- **Channel restrictions**: Only monitors specifically configured channels

---

*Last updated: 2025-05-28*
*Feature status: Production ready with complete correlation tracking*