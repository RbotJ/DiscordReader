# Discord Bot Permission Issue - Fix Required

## Current Problem
The Discord bot cannot sync message history because it lacks the "Read Message History" permission in the #aplus-setups channel.

## Required Permissions
The bot needs these permissions in the #aplus-setups channel:
1. **View Channel** - To see the channel
2. **Read Message History** - To fetch past messages for manual sync
3. **Send Messages** - For any future features
4. **Read Messages** - To receive real-time messages

## How to Fix (Discord Server Admin Required)

### Method 1: Channel-Specific Permissions
1. Right-click on the #aplus-setups channel in Discord
2. Select "Edit Channel"
3. Go to "Permissions" tab
4. Click "+" to add a role/member
5. Select the "Aplus" bot role
6. Enable these permissions:
   - ✅ View Channel
   - ✅ Send Messages  
   - ✅ Read Message History
   - ✅ Read Messages

### Method 2: Role-Based Permissions
1. Go to Server Settings → Roles
2. Find the "Aplus" bot role
3. Enable these permissions at the role level:
   - ✅ View Channels
   - ✅ Send Messages
   - ✅ Read Message History

## Verification
After updating permissions, the manual sync should work and return actual message counts instead of 0.

## Current Bot Status
- ✅ Bot is connected and online
- ✅ Target channel is detected (#aplus-setups)
- ❌ Cannot read message history due to permissions
- ✅ Uptime counter is now working