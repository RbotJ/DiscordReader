# Dashboard Feature - Interactive Monitoring Interface

The Dashboard feature provides comprehensive operational monitoring with real-time event analytics, correlation flow tracking, and interactive data visualization.

## Overview

This feature implements an interactive web dashboard that displays operational telemetry for the trading platform, including Discord message processing, setup parsing, and system health monitoring with live updates.

## Key Components

### API Routes (`api_routes.py`)
- **Event Analytics API**: Filter and query operational events
- **Correlation Flow Tracking**: Trace complete message journeys  
- **Statistics Endpoint**: Operational health metrics and analytics
- **Enhanced Status**: Combined system status with event insights

### Data Service (`services/data_service.py`)
- **System Status**: Aggregate operational data from multiple sources
- **Database Queries**: Efficient data retrieval with proper error handling
- **Data Transformation**: Convert raw data into dashboard-friendly formats

### Templates (`templates/dashboard/status.html`)
- **Interactive UI**: Real-time event filtering and display
- **Operational Health**: Visual health indicators and status badges
- **Event Timeline**: Chronological display of operational events
- **Correlation Links**: Clickable correlation ID tracking

## API Endpoints

### Event Analytics
```
GET /dashboard/events
Query Parameters:
  - channel: Filter by event channel
  - event_type: Filter by event type  
  - source: Filter by event source
  - hours: Hours to look back (default: 24)
  - limit: Maximum events to return (default: 100)
```

### Correlation Flow Tracking
```
GET /dashboard/events/correlation/{correlation_id}
Returns complete timeline of events for correlation ID
```

### Event Statistics
```
GET /dashboard/events/statistics
Query Parameters:
  - hours: Hours to calculate stats for (default: 24)

Returns operational health metrics and event breakdowns
```

### Enhanced Status
```
GET /dashboard/status/enhanced
Combines existing dashboard data with event analytics
```

### Correlation Flows
```
GET /dashboard/correlation-flows
Query Parameters:
  - hours: Hours to look back (default: 24)
  - limit: Maximum flows to return (default: 20)

Returns recent correlation flows with metadata
```

## Dashboard Features

### Real-time Event Monitoring
- **Auto-refresh**: Events update every 30 seconds automatically
- **Live filtering**: Dynamic event filtering by channel and time range
- **Interactive controls**: Dropdown filters for channel and time selection
- **Event details**: Structured display of event metadata and payloads

### Operational Health Indicators
- **Health scoring**: Automatic calculation based on event patterns
- **Visual status**: Color-coded badges (Healthy/Warning/Critical)  
- **Activity monitoring**: Track Discord, ingestion, and parsing activity
- **Error detection**: Identify system issues through event analysis

### Correlation Flow Visualization
- **Flow tracing**: Click correlation IDs to see complete event timelines
- **Journey mapping**: Visual representation of message-to-setup flows
- **Timeline display**: Chronological event ordering with timestamps
- **Flow completion**: Track which flows complete successfully

## Event Channel Visualization

### Channel Badge System
- **Discord Messages**: Blue badges for `discord:message`
- **Ingestion Events**: Info badges for `ingestion:message`  
- **Parsing Events**: Success badges for `parsing:setup`
- **Bot Events**: Warning badges for `bot:startup`
- **System Events**: Danger badges for `system`

### Event Type Classification
- **Error Events**: Red badges for error-type events
- **Warning Events**: Yellow badges for warning events
- **Success Events**: Green badges for parsed/completed events
- **Info Events**: Light badges for general information

## Integration Points

### Enhanced Event System
- **Real-time data**: Direct integration with PostgreSQL event bus
- **Correlation tracking**: Full visibility into event relationships
- **Performance metrics**: Event volume and processing analytics

### Discord Bot Integration  
- **Bot status**: Real-time Discord bot connection monitoring
- **Message tracking**: Live display of Discord message processing
- **Channel activity**: Monitor which channels are most active

### System Health Monitoring
- **Operational scoring**: Automated health calculation from event patterns
- **Error rate tracking**: Monitor system error rates and trends
- **Performance indicators**: Processing speed and success rates

## Dashboard UI Components

### Status Overview Cards
- **Recent Messages**: Count of recent Discord messages processed
- **Today's Messages**: Daily message volume tracking
- **Parsed Setups**: Successfully extracted trading setups
- **Active Tickers**: Number of unique tickers being monitored

### Event Timeline Table
- **Timestamp**: When each event occurred
- **Channel**: Color-coded event channel badges
- **Event Type**: Categorized event type indicators
- **Source**: Which service/module generated the event
- **Details**: Key information from event payload
- **Correlation**: Clickable links to trace related events

### Interactive Controls
- **Channel Filter**: Dropdown to filter by specific event channels
- **Time Range**: Select from 2 hours, 6 hours, or 24 hours
- **Refresh Button**: Manual refresh trigger with loading indicators
- **Health Badge**: Live operational health status display

## Styling & User Experience

### Bootstrap Integration
- **Responsive design**: Works on desktop and mobile devices
- **Clean interface**: Modern card-based layout with proper spacing
- **Accessible controls**: Clear labels and intuitive interactions
- **Loading states**: Spinner indicators during data fetching

### Color Coding System
- **Health Status**: Green (healthy), yellow (warning), red (critical)
- **Event Channels**: Consistent color scheme across all views
- **Event Types**: Error/warning/success color classification
- **Interactive Elements**: Hover states and active indicators

## Performance Optimization

### Efficient Data Loading
- **Pagination**: Limit results to prevent overwhelming interface
- **Smart queries**: Optimized database queries with proper indexes
- **Caching strategy**: Minimize repeated database calls
- **Progressive loading**: Load critical data first, details on demand

### Real-time Updates
- **Auto-refresh**: Non-blocking background updates every 30 seconds
- **Error handling**: Graceful degradation when updates fail
- **User feedback**: Clear indicators when data is being refreshed
- **State preservation**: Maintain user filter selections during updates

## Error Handling

### API Error Management
- **Graceful failures**: User-friendly error messages for API failures
- **Retry logic**: Automatic retry for transient network issues
- **Fallback display**: Show last known data when updates fail
- **Error logging**: Log client-side errors for debugging

### UI Error States
- **Loading indicators**: Show progress during data fetching
- **Empty states**: Informative messages when no data available
- **Connection issues**: Clear indication when backend unavailable
- **Validation feedback**: Immediate feedback for invalid inputs

## Monitoring & Analytics

### Usage Tracking
```javascript
// Track dashboard usage patterns
- Page views and session duration
- Most used filters and time ranges  
- Correlation flow clicks and exploration
- Error rates and user experience issues
```

### Performance Metrics
```sql
-- Dashboard query performance
SELECT 
    endpoint,
    AVG(response_time_ms) as avg_response,
    COUNT(*) as request_count
FROM api_logs 
WHERE endpoint LIKE '/dashboard/%'
GROUP BY endpoint;
```

## Security Considerations

### Access Control
- **No authentication currently**: Single-user application assumption
- **Future enhancement**: Role-based access control ready for implementation
- **Data exposure**: Only operational data exposed, no sensitive trading data
- **CSRF protection**: Standard Flask security measures applied

### Data Privacy
- **Operational focus**: Dashboard shows system events, not personal data
- **Correlation IDs**: UUIDs provide correlation without exposing sensitive info
- **Event filtering**: Users can filter out sensitive event types if needed

---

*Last updated: 2025-05-28*
*Feature status: Production ready with real-time operational monitoring*