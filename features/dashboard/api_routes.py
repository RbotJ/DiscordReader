"""
Enhanced Dashboard API Routes

Provides event analytics endpoints for operational monitoring and real-time data.
Integrates with the enhanced event system for comprehensive telemetry.
"""
import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from typing import Dict, Any, List

from common.events.query_service import EventQueryService
from common.event_constants import EventChannels, EventTypes

logger = logging.getLogger(__name__)

# Create blueprint for dashboard API routes
dashboard_api = Blueprint('dashboard_api', __name__, url_prefix='/dashboard')


@dashboard_api.route('/events', methods=['GET'])
def get_events():
    """
    Get filtered events for operational monitoring.
    
    Query parameters:
        - channel: Filter by event channel
        - event_type: Filter by event type
        - source: Filter by event source
        - hours: Hours to look back (default: 24)
        - limit: Maximum events to return (default: 100)
    """
    try:
        # Parse query parameters
        channel = request.args.get('channel')
        event_type = request.args.get('event_type')
        source = request.args.get('source')
        hours = int(request.args.get('hours', 24))
        limit = int(request.args.get('limit', 100))
        
        # Get events based on filters
        if channel:
            since = datetime.utcnow() - timedelta(hours=hours)
            events = EventQueryService.get_events_by_channel(channel, since, limit)
        elif event_type:
            since = datetime.utcnow() - timedelta(hours=hours)
            events = EventQueryService.get_events_by_type(event_type, since, limit)
        elif source:
            since = datetime.utcnow() - timedelta(hours=hours)
            events = EventQueryService.get_events_by_source(source, since, limit)
        else:
            # Get recent events with operational focus
            operational_channels = [
                EventChannels.DISCORD_MESSAGE,
                EventChannels.INGESTION_MESSAGE,
                EventChannels.PARSING_SETUP,
                EventChannels.BOT_STARTUP,
                EventChannels.SYSTEM
            ]
            events = EventQueryService.get_recent_events(hours, operational_channels, limit)
        
        # Convert events to JSON-serializable format
        event_data = [event.to_dict() for event in events]
        
        return jsonify({
            'success': True,
            'events': event_data,
            'count': len(event_data),
            'filters': {
                'channel': channel,
                'event_type': event_type,
                'source': source,
                'hours': hours,
                'limit': limit
            }
        })
        
    except Exception as e:
        logger.error(f"Error retrieving events: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dashboard_api.route('/events/correlation/<correlation_id>', methods=['GET'])
def get_correlation_flow(correlation_id: str):
    """
    Get all events with the same correlation ID for flow tracing.
    
    Args:
        correlation_id: UUID string for correlation tracking
    """
    try:
        events = EventQueryService.get_events_by_correlation(correlation_id)
        
        if not events:
            return jsonify({
                'success': False,
                'message': f'No events found for correlation ID: {correlation_id}'
            }), 404
        
        # Convert events to timeline format
        timeline = []
        for event in events:
            timeline.append({
                'id': event.id,
                'timestamp': event.created_at.isoformat(),
                'channel': event.channel,
                'event_type': event.event_type,
                'source': event.source,
                'data': event.data
            })
        
        return jsonify({
            'success': True,
            'correlation_id': correlation_id,
            'timeline': timeline,
            'count': len(timeline)
        })
        
    except Exception as e:
        logger.error(f"Error retrieving correlation flow: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dashboard_api.route('/events/statistics', methods=['GET'])
def get_event_statistics():
    """
    Get event statistics for operational monitoring.
    
    Query parameters:
        - hours: Hours to calculate stats for (default: 24)
    """
    try:
        hours = int(request.args.get('hours', 24))
        since = datetime.utcnow() - timedelta(hours=hours)
        
        stats = EventQueryService.get_event_statistics(since)
        
        # Add operational insights
        operational_stats = {
            **stats,
            'operational_health': _calculate_operational_health(stats),
            'timeframe_hours': hours
        }
        
        return jsonify({
            'success': True,
            'statistics': operational_stats
        })
        
    except Exception as e:
        logger.error(f"Error calculating event statistics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dashboard_api.route('/status/enhanced', methods=['GET'])
def get_enhanced_status():
    """
    Enhanced status endpoint combining existing dashboard data with event analytics.
    """
    try:
        # Get existing dashboard data from basic status endpoint
        try:
            from features.dashboard.services.data_service import get_system_status
            existing_status = get_system_status()
        except ImportError:
            existing_status = {'success': True, 'message': 'Basic status data unavailable'}
        
        # Get recent operational events (last 2 hours)
        recent_events = EventQueryService.get_recent_events(
            hours=2,
            channels=[
                EventChannels.DISCORD_MESSAGE,
                EventChannels.INGESTION_MESSAGE,
                EventChannels.PARSING_SETUP,
                EventChannels.ALERT_SYSTEM,
                EventChannels.BOT_STARTUP
            ],
            limit=50
        )
        
        # Get event statistics for operational health
        event_stats = EventQueryService.get_event_statistics(
            since=datetime.utcnow() - timedelta(hours=24)
        )
        
        # Enhanced status response
        enhanced_status = {
            **existing_status,
            'events': {
                'recent_count': len(recent_events),
                'recent_events': [event.to_dict() for event in recent_events[:10]],
                'statistics': event_stats,
                'operational_health': _calculate_operational_health(event_stats)
            }
        }
        
        return jsonify(enhanced_status)
        
    except Exception as e:
        logger.error(f"Error getting enhanced status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _calculate_operational_health(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate operational health metrics from event statistics.
    
    Args:
        stats: Event statistics dictionary
        
    Returns:
        Dict containing health metrics
    """
    try:
        total_events = stats.get('total_events', 0)
        channels = stats.get('channels', {})
        sources = stats.get('sources', {})
        
        # Calculate health indicators
        discord_activity = channels.get(EventChannels.DISCORD_MESSAGE, 0)
        ingestion_activity = channels.get(EventChannels.INGESTION_MESSAGE, 0)
        parsing_activity = channels.get(EventChannels.PARSING_SETUP, 0)
        system_errors = channels.get(EventChannels.SYSTEM, 0)
        
        # Health scoring
        health_score = 100
        if total_events == 0:
            health_score = 50  # No activity
        elif system_errors > (total_events * 0.1):
            health_score = 30  # High error rate
        elif ingestion_activity == 0 and discord_activity > 0:
            health_score = 60  # Discord active but ingestion not working
        elif parsing_activity == 0 and ingestion_activity > 0:
            health_score = 70  # Ingestion working but parsing issues
        
        return {
            'score': health_score,
            'status': 'healthy' if health_score >= 80 else 'warning' if health_score >= 50 else 'critical',
            'indicators': {
                'discord_messages': discord_activity,
                'ingestion_events': ingestion_activity,
                'parsing_events': parsing_activity,
                'system_errors': system_errors,
                'total_events': total_events
            }
        }
        
    except Exception as e:
        logger.error(f"Error calculating operational health: {e}")
        return {
            'score': 0,
            'status': 'unknown',
            'error': str(e)
        }


@dashboard_api.route('/correlation-flows', methods=['GET'])
def get_correlation_flows():
    """
    Get recent correlation flows for Discord message tracing.
    
    Query parameters:
        - hours: Hours to look back for flows (default: 24)
        - limit: Maximum flows to return (default: 20)
    """
    try:
        hours = int(request.args.get('hours', 24))
        limit = int(request.args.get('limit', 20))
        
        # Get recent events with correlation IDs
        since = datetime.utcnow() - timedelta(hours=hours)
        events = EventQueryService.get_recent_events(hours, None, 1000)
        
        # Group by correlation ID
        correlation_flows = {}
        for event in events:
            if event.correlation_id:
                corr_id = str(event.correlation_id)
                if corr_id not in correlation_flows:
                    correlation_flows[corr_id] = {
                        'correlation_id': corr_id,
                        'events': [],
                        'start_time': event.created_at,
                        'end_time': event.created_at,
                        'channels': set(),
                        'sources': set()
                    }
                
                flow = correlation_flows[corr_id]
                flow['events'].append(event.to_dict())
                flow['channels'].add(event.channel)
                flow['sources'].add(event.source or 'unknown')
                
                # Update timespan
                if event.created_at < flow['start_time']:
                    flow['start_time'] = event.created_at
                if event.created_at > flow['end_time']:
                    flow['end_time'] = event.created_at
        
        # Convert sets to lists and sort by start time
        flows = []
        for flow in correlation_flows.values():
            flow['channels'] = list(flow['channels'])
            flow['sources'] = list(flow['sources'])
            flow['event_count'] = len(flow['events'])
            flow['duration_seconds'] = (flow['end_time'] - flow['start_time']).total_seconds()
            flow['start_time'] = flow['start_time'].isoformat()
            flow['end_time'] = flow['end_time'].isoformat()
            flows.append(flow)
        
        # Sort by start time descending and limit
        flows.sort(key=lambda x: x['start_time'], reverse=True)
        flows = flows[:limit]
        
        return jsonify({
            'success': True,
            'flows': flows,
            'count': len(flows),
            'total_correlations': len(correlation_flows)
        })
        
    except Exception as e:
        logger.error(f"Error retrieving correlation flows: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500