# Database Schema Documentation

This document describes the current database schema for the A+ Trading App, including all tables created during the enhanced event system implementation.

## 📊 Current Database Tables

### New Schema Tables (Enhanced Event System)

#### `events` - Enhanced Event Bus
Primary table for the PostgreSQL-based event system with correlation tracking.

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

-- Indexes for performance
CREATE INDEX idx_events_channel ON events(channel);
CREATE INDEX idx_events_event_type ON events(event_type);
CREATE INDEX idx_events_source ON events(source);
CREATE INDEX idx_events_correlation_id ON events(correlation_id);
CREATE INDEX idx_events_created_at ON events(created_at);
CREATE INDEX idx_events_data_gin ON events USING GIN (data);
```

**Purpose**: Central event logging with correlation tracking for Discord message flows.

#### `discord_channels` - Channel Management
Stores Discord channel information for monitoring and ingestion.

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

**Purpose**: Track which Discord channels are being monitored for trading messages.

#### `discord_messages` - Message Storage
Stores Discord messages for ingestion and processing.

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

**Purpose**: Store Discord messages for parsing and setup extraction.

#### `trade_setups` - Setup Storage
Stores parsed trading setups from Discord messages.

```sql
CREATE TABLE trade_setups (
  id SERIAL PRIMARY KEY,
  ticker VARCHAR(10) NOT NULL,
  setup_type VARCHAR(50),
  direction VARCHAR(10),
  price_target DECIMAL(10,2),
  confidence DECIMAL(3,2),
  source VARCHAR(50) DEFAULT 'discord',
  message_id VARCHAR(255),
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Purpose**: Store parsed trading setups with their metadata and confidence levels.

#### `parsed_levels` - Price Level Storage
Stores parsed price levels and targets from trading setups.

```sql
CREATE TABLE parsed_levels (
  id SERIAL PRIMARY KEY,
  setup_id INTEGER REFERENCES trade_setups(id),
  level_type VARCHAR(20),
  price_value DECIMAL(10,2),
  description TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Purpose**: Store individual price levels (targets, stops, etc.) associated with setups.

### Legacy Tables (Preserved with "old_" prefix)

All previous tables have been renamed with "old_" prefix to preserve existing data:

- `old_setups` - Original setup data
- `old_setup_channels` - Original channel configuration
- `old_ingestion_status` - Original ingestion tracking
- `old_events` - Original event logging

## 🔄 Event System Integration

### Event Channels
- `discord:message` - Discord message events
- `ingestion:message` - Message ingestion events
- `parsing:setup` - Setup parsing events
- `setup:created` - Setup creation events
- `bot:startup` - Bot lifecycle events
- `system` - System-level events

### Event Types
- `discord.message.received` - Message received from Discord
- `ingestion.message.stored` - Message stored in database
- `parsing.setup.parsed` - Setup successfully parsed
- `setup.created` - New setup created
- `system.error` - System error events

### Correlation Tracking
Events are linked using UUID correlation IDs to trace complete flows:
Discord Message → Ingestion → Parsing → Setup Creation

## 📈 Data Flow Architecture

```
Discord Message
       ↓
[discord_messages] ← Event: discord.message.received
       ↓
   Ingestion ← Event: ingestion.message.stored
       ↓
    Parsing ← Event: parsing.setup.parsed
       ↓
[trade_setups] ← Event: setup.created
       ↓
[parsed_levels]
```

All steps are tracked in the `events` table with correlation IDs linking the complete flow.

## 🛠️ Database Functions

### Event Cleanup
Automatic cleanup function for 90-day retention policy:

```sql
CREATE OR REPLACE FUNCTION cleanup_old_events()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM events 
    WHERE created_at < NOW() - INTERVAL '90 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
```

## 🔧 Maintenance

### Indexes
All tables have appropriate indexes for:
- Primary key lookups
- Foreign key relationships
- Time-based queries
- JSONB payload searches (GIN indexes)

### Retention
- Events: 90-day automatic cleanup
- Discord messages: Indefinite retention
- Setups: Indefinite retention
- Parsed levels: Indefinite retention

## 📊 Monitoring Queries

### Recent Events by Channel
```sql
SELECT channel, event_type, COUNT(*) 
FROM events 
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY channel, event_type
ORDER BY COUNT(*) DESC;
```

### Correlation Flow Tracking
```sql
SELECT 
  correlation_id,
  COUNT(*) as event_count,
  MIN(created_at) as flow_start,
  MAX(created_at) as flow_end
FROM events 
WHERE correlation_id IS NOT NULL
  AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY correlation_id
ORDER BY flow_start DESC;
```

### Setup Creation Rate
```sql
SELECT 
  DATE(created_at) as date,
  COUNT(*) as setups_created
FROM trade_setups
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

---

*Last updated: 2025-05-28*
*Schema version: v2.0 (Enhanced Event System)*