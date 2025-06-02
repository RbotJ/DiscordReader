# Discord Bot Feature - Live Operational Monitoring

The Discord Bot feature provides real-time message monitoring with live metrics dashboard, in-memory message counting, and trading alert detection for comprehensive operational visibility.

## Overview

This feature implements a Discord bot with live operational metrics that monitors trading channels, counts messages in real-time, detects trading alerts, and provides an operational dashboard independent of database storage for maximum reliability.

## Key Components

### Discord Bot (`bot.py`)
- **TradingDiscordBot class**: Main Discord client with live metrics tracking
- **In-memory counters**: Real-time message counting (`_messages_today`, `_triggers_today`)
- **Trading alert detection**: Keyword-based classification of trading-related messages
- **Daily reset functionality**: Automatic counter reset at midnight
- **Channel monitoring**: Monitors configured target channel for message activity
- **Flask integration**: Bot instance stored in `app.config['DISCORD_BOT']` for API access

### Live Metrics API (`api.py`)
- **Real-time endpoint**: `/api/discord/metrics` returns live bot status and counters
- **Connection status**: Bot connectivity, latency, and health monitoring
- **Message metrics**: Live counts of daily messages and trading alerts
- **Database-independent**: Metrics work regardless of database connectivity issues

### Operational Dashboard (`dashboard.py`)
- **Real-time dashboard**: `/dashboard/discord/` with live metrics display
- **Auto-refresh**: Frontend updates every 5 seconds via JavaScript
- **Live counters**: Messages Today and Trading Alerts with "Live" indicators
- **Connection monitoring**: Real-time bot status and latency display

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

## Live Metrics System

### In-Memory Counters
The bot maintains real-time metrics in memory for immediate operational visibility:

```python
class TradingDiscordBot:
    def __init__(self):
        self._messages_today = 0          # Total messages received today
        self._triggers_today = 0          # Trading alerts detected today
        self._last_reset_date = None      # Last counter reset date
        self.aplus_setups_channel_id = None  # Target channel ID
```

### Trading Alert Detection
Messages are classified as trading alerts using keyword matching:
```python
TRADING_KEYWORDS = [
    'breakout', 'breakdown', 'bounce', 'rejection',
    'calls', 'puts', 'strike', 'expiry', 'target',
    'stop', 'entry', 'exit', 'alert', 'signal'
]
```

### Daily Reset Logic
Counters automatically reset at midnight to track daily activity:
```python
def _check_daily_reset(self):
    today = datetime.now().date()
    if self._last_reset_date != today:
        self._messages_today = 0
        self._triggers_today = 0
        self._last_reset_date = today
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

## API Endpoints

### Live Metrics API
**GET** `/api/discord/metrics`

Returns real-time bot status and message counters:
```json
{
  "connected": true,
  "latency_ms": 38,
  "live_messages_today": 15,
  "triggers_today": 3,
  "target_channel_id": "1372012942848954388",
  "last_reset_date": "2025-06-02"
}
```

### Dashboard Routes
- **GET** `/dashboard/discord/` - Live operational dashboard
- **GET** `/dashboard/discord/metrics.json` - Dashboard metrics endpoint

## Configuration

### Environment Variables
```bash
# Required
DISCORD_BOT_TOKEN=your_bot_token_here

# Optional (auto-detected if not provided)
DISCORD_GUILD_ID=your_guild_id
DISCORD_CHANNEL_ID=your_channel_id
```

### Flask Integration
The bot instance is stored in Flask app configuration for API access:
```python
# In app.py startup
app.config['DISCORD_BOT'] = bot

# In API endpoints
bot = current_app.config.get('DISCORD_BOT')
if bot:
    metrics = {
        'connected': bot.is_ready(),
        'live_messages_today': bot._messages_today,
        'triggers_today': bot._triggers_today
    }
```

## Usage Examples

### Accessing Live Metrics
```python
from flask import current_app

# Get bot instance from Flask app
bot = current_app.config.get('DISCORD_BOT')
if bot:
    print(f"Connected: {bot.is_ready()}")
    print(f"Messages today: {bot._messages_today}")
    print(f"Trading alerts: {bot._triggers_today}")
    print(f"Target channel: {bot.aplus_setups_channel_id}")
```

### Frontend Live Updates
```javascript
// JavaScript for real-time dashboard updates
async function updateLiveMetrics() {
    try {
        const response = await fetch('/api/discord/metrics');
        const data = await response.json();
        
        document.getElementById('live-messages-today').textContent = data.live_messages_today || 0;
        document.getElementById('trigger-messages-today').textContent = data.triggers_today || 0;
    } catch (error) {
        console.error('Error fetching live metrics:', error);
    }
}

// Update every 5 seconds
setInterval(updateLiveMetrics, 5000);
```

### Manual Counter Reset
```python
# Force reset counters (normally automatic at midnight)
if bot:
    bot._messages_today = 0
    bot._triggers_today = 0
    bot._last_reset_date = datetime.now().date()
```

## Integration Points

### Ingestion Service Integration
- **Direct service calls**: Bot calls ingestion service methods directly
- **Dependency injection**: Ingestion service provided via constructor
- **Error isolation**: Ingestion failures don't crash the bot

### Dashboard Integration
- **Live operational dashboard**: Real-time metrics at `/dashboard/discord/`
- **Auto-refresh frontend**: Updates every 5 seconds without page reload
- **Visual indicators**: "Live" badges distinguish real-time from historical data
- **Connection monitoring**: Real-time status, latency, and health display

### Flask App Integration
- **Bot storage**: Instance stored in `app.config['DISCORD_BOT']` for API access
- **Route registration**: API and dashboard blueprints registered in `app.py`
- **Background operation**: Bot runs in separate thread while Flask serves requests
- **Graceful fallback**: Application continues if bot fails to start

## Bot Lifecycle

### Startup Sequence
1. **Environment validation**: Check required Discord credentials
2. **Flask integration**: Store bot instance in `app.config['DISCORD_BOT']`
3. **Channel discovery**: Scan guilds for #aplus-setups channels
4. **Counter initialization**: Set up in-memory message counters
5. **Real-time monitoring**: Begin monitoring target channel for new messages

### Runtime Operations
- **Live message counting**: Increment counters for each message received
- **Trading alert detection**: Classify messages using keyword matching
- **Daily reset**: Automatic counter reset at midnight
- **API availability**: Serve live metrics via `/api/discord/metrics`
- **Dashboard updates**: Real-time frontend updates every 5 seconds

### Operational Benefits
- **Database independence**: Metrics work even during database outages
- **Real-time visibility**: Immediate operational insights without delays
- **Lightweight operation**: In-memory counters minimize performance impact
- **Reliable monitoring**: Bot status always available through live API

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

### Live Metrics Monitoring
```bash
# Check real-time bot status
curl http://localhost:5000/api/discord/metrics

# Expected response
{
  "connected": true,
  "latency_ms": 38,
  "live_messages_today": 15,
  "triggers_today": 3,
  "target_channel_id": "1372012942848954388",
  "last_reset_date": "2025-06-02"
}
```

### Dashboard Monitoring
- **Live dashboard**: Visit `/dashboard/discord/` for real-time operational view
- **Auto-refresh**: Metrics update every 5 seconds automatically
- **Visual indicators**: "Live" badges show real-time data vs historical
- **Connection status**: Real-time bot connectivity and latency display

### Bot Health Verification
```python
from flask import current_app

# Check bot status in Flask context
bot = current_app.config.get('DISCORD_BOT')
if bot:
    print(f"Bot ready: {bot.is_ready()}")
    print(f"Latency: {bot.latency * 1000:.0f}ms")
    print(f"Target channel: {bot.aplus_setups_channel_id}")
    print(f"Daily messages: {bot._messages_today}")
    print(f"Trading alerts: {bot._triggers_today}")
```

### Performance Characteristics
- **Memory footprint**: Minimal - only stores daily counters
- **Response time**: Sub-millisecond metric access from memory
- **Reliability**: Independent of database connectivity
- **Real-time updates**: 5-second refresh cycle for operational visibility

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

*Last updated: 2025-06-02*
*Feature status: Production ready with live operational metrics and real-time dashboard*