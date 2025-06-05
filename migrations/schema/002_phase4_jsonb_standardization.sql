-- Phase 4.2: JSONB Column Standardization
-- Standardize all JSONB columns to use 'data' naming convention

-- Step 1: Add standardized 'data' columns where needed
ALTER TABLE discord_messages 
ADD COLUMN IF NOT EXISTS message_data JSONB;

-- Step 2: Migrate existing JSONB data to standardized columns
-- Consolidate embed_data, attachment_data, and raw_data into message_data
UPDATE discord_messages 
SET message_data = COALESCE(
    CASE 
        WHEN raw_data IS NOT NULL THEN raw_data
        ELSE jsonb_build_object(
            'embeds', COALESCE(embed_data, '[]'::jsonb),
            'attachments', COALESCE(attachment_data, '[]'::jsonb)
        )
    END,
    '{}'::jsonb
);

-- Step 3: Add version field to standardized data
UPDATE discord_messages 
SET message_data = message_data || jsonb_build_object('schema_version', '2.0')
WHERE message_data IS NOT NULL;

-- Step 4: Add validation for standardized JSONB structure
ALTER TABLE discord_messages 
ADD CONSTRAINT IF NOT EXISTS chk_message_data_structure 
CHECK (
    message_data IS NULL OR 
    (jsonb_typeof(message_data) = 'object' AND 
     message_data ? 'schema_version')
);

-- Step 5: Update events table to include schema versioning
UPDATE events 
SET data = data || jsonb_build_object('schema_version', '2.0')
WHERE data IS NOT NULL AND NOT (data ? 'schema_version');

-- Step 6: Add event data validation
ALTER TABLE events 
ADD CONSTRAINT IF NOT EXISTS chk_events_data_structure 
CHECK (
    data IS NOT NULL AND 
    jsonb_typeof(data) = 'object'
);

-- Record migration
INSERT INTO schema_migrations (version, description, checksum) 
VALUES ('4.2.0', 'JSONB standardization and validation', 'phase4_jsonb_002')
ON CONFLICT (version) DO NOTHING;