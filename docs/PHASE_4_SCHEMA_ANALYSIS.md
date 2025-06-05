# Phase 4: Database Schema Analysis

## Current Schema State

### Active Tables
1. **events** - Event bus storage (JSONB data column) ✓
2. **discord_channels** - Channel management 
3. **discord_messages** - Message storage (multiple JSONB columns)
4. **trade_setups** - Trading setup data (JSONB watch_levels)
5. **parsed_levels** - Parsed trading levels

### Legacy Tables (old_* prefix)
- old_events, old_market_data, old_orders, old_positions, etc.
- Contains legacy data with inconsistent schema patterns

## Schema Inconsistencies Identified

### 1. Event Data Column Naming
- **events** table: Uses `data` (JSONB) ✓ CORRECT
- **discord_messages** table: Uses `embed_data`, `attachment_data`, `raw_data` (JSONB)
- **trade_setups** table: Uses `watch_levels` (JSONB)
- **old_events** table: Uses `data` (JSONB) ✓

**Action Required**: Standardize on `data` for primary JSONB storage

### 2. Missing NOT NULL Constraints
- discord_channels.name (nullable but should be required)
- discord_messages.content (nullable but should validate)
- discord_messages.author_id (nullable but should be required)
- discord_messages.channel_id (nullable but should be required)

### 3. Missing Indexes for Performance
- discord_messages.channel_id (no index for channel queries)
- discord_messages.author_id (no index for author queries)
- discord_messages.created_at (no index for time-based queries)
- trade_setups.ticker (no index for symbol lookups)

### 4. Foreign Key Relationships Missing
- discord_messages -> discord_channels (channel_id relationship)
- parsed_levels -> trade_setups (setup_id exists but could be enhanced)

### 5. Event Schema Validation
- No validation on JSONB event data structure
- No versioning system for event schema evolution
- No enforcement of required event fields

## Recommended Migration Plan

### Phase 4.1: Safe NOT NULL Migrations
1. Audit existing NULL data
2. Backfill with appropriate defaults
3. Add NOT NULL constraints

### Phase 4.2: Event Schema Standardization
1. Rename JSONB columns to `data`
2. Implement event validation
3. Add schema versioning

### Phase 4.3: Performance Optimization
1. Add missing indexes
2. Optimize query patterns
3. Add foreign key constraints

### Phase 4.4: Validation Framework
1. Implement Pydantic event schemas
2. Add validation middleware
3. Create monitoring for schema violations