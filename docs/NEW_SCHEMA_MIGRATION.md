# A+ Trading Database Schema Migration

## ✅ Completed: New Setup Parsing Schema

### New Tables Created

1. **`new_discord_channels`** - Discord channel management
   - Centralized channel configuration
   - Listen/announce flags for bot behavior
   - Activity tracking

2. **`new_discord_messages`** - Raw message storage
   - Unique message ID tracking
   - Channel relationship
   - Processing status flags

3. **`new_trade_setups`** - Ticker setup containers
   - One setup per ticker per trading day
   - Links to source Discord message
   - Bias notes and activity status

4. **`new_parsed_levels`** - Individual trading levels
   - Breakouts, breakdowns, bounces, rejections
   - Multiple targets per level
   - Strategy classification (aggressive/conservative)

### Migration Status
- ✅ Alembic migration created and executed
- ✅ New tables created with proper relationships
- ✅ Foreign key constraints implemented
- ✅ SQLAlchemy models defined

## 🔄 Next Steps Required

### 1. Update Features to Use New Schema
- [ ] Modify ingestion pipeline to write to `new_discord_messages`
- [ ] Update parser to create `new_trade_setups` and `new_parsed_levels`
- [ ] Refactor dashboard to query new tables

### 2. Deprecation Strategy
- [ ] Mark old tables as deprecated (keep data intact)
- [ ] Stop all new writes to old tables
- [ ] Create data migration utilities if needed

### 3. Testing & Verification
- [ ] Test new ingestion flow
- [ ] Verify parser creates proper relationships
- [ ] Ensure dashboard displays new data correctly

## 📊 Schema Benefits

**Before:** Fragmented data across multiple tables
- `trade_setups` (inconsistent structure)
- `ticker_setups` (incomplete relationships)
- `setup_messages` (parsing confusion)

**After:** Clean normalized structure
- Clear data flow: Discord → Message → Setup → Levels
- Proper foreign key relationships
- Consistent column naming
- Better query performance

## 🚀 Implementation Priority

1. **High Priority:** Update system status dashboard to use new tables
2. **Medium Priority:** Refactor ingestion and parsing features
3. **Low Priority:** Data migration from old tables (after validation)

This restructuring provides a solid foundation for reliable setup parsing and eliminates the data inconsistencies we discovered earlier.