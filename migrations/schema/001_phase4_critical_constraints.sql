-- Phase 4.1: Critical NOT NULL constraints migration
-- This migration safely adds NOT NULL constraints after data backfill

-- Step 1: Add NOT NULL constraint to discord_channels.name (already applied)
-- ALTER TABLE discord_channels ALTER COLUMN name SET NOT NULL;

-- Step 2: Add missing indexes for performance (already applied)
-- CREATE INDEX idx_discord_messages_channel_id ON discord_messages(channel_id);
-- CREATE INDEX idx_discord_messages_author_id ON discord_messages(author_id);
-- CREATE INDEX idx_discord_messages_created_at ON discord_messages(created_at);

-- Step 3: Add remaining performance indexes
CREATE INDEX IF NOT EXISTS idx_trade_setups_ticker 
ON trade_setups(ticker);

CREATE INDEX IF NOT EXISTS idx_discord_channels_guild_id 
ON discord_channels(guild_id);

CREATE INDEX IF NOT EXISTS idx_parsed_levels_setup_id 
ON parsed_levels(setup_id);

-- Step 4: Add check constraints for data validation
ALTER TABLE discord_messages 
ADD CONSTRAINT IF NOT EXISTS chk_discord_messages_content_length 
CHECK (length(content) <= 4000);

ALTER TABLE discord_channels 
ADD CONSTRAINT IF NOT EXISTS chk_discord_channels_name_length 
CHECK (length(name) > 0 AND length(name) <= 100);

-- Step 5: Add schema version tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    checksum VARCHAR(64)
);

INSERT INTO schema_migrations (version, description, checksum) 
VALUES ('4.1.0', 'Phase 4 critical constraints and indexes', 'phase4_critical_001')
ON CONFLICT (version) DO NOTHING;