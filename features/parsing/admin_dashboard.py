"""
Admin Dashboard for Advanced Parsing Metrics and Debugging

Provides detailed breakdown of parsing accuracy, failure analysis,
and data quality metrics for administrative monitoring.
"""

from flask import Blueprint, render_template, jsonify
from features.parsing.store import get_parsing_store
from sqlalchemy import text
import logging
from datetime import datetime, date
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

admin_parsing_bp = Blueprint('admin_parsing', __name__, url_prefix='/admin/parsing')

@admin_parsing_bp.route('/breakdown')
def parsing_breakdown():
    """Detailed parsing breakdown for administrative monitoring."""
    try:
        store = get_parsing_store()
        
        # Get comprehensive metrics
        metrics = get_comprehensive_metrics(store)
        
        return render_template('parsing/admin_breakdown.html', **metrics)
        
    except Exception as e:
        logger.error(f"Error in parsing breakdown: {e}")
        return f"Error loading parsing breakdown: {e}", 500

@admin_parsing_bp.route('/api/breakdown')
def api_parsing_breakdown():
    """API endpoint for parsing breakdown data."""
    try:
        store = get_parsing_store()
        metrics = get_comprehensive_metrics(store)
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Error in API breakdown: {e}")
        return jsonify({'error': str(e)}), 500

def get_comprehensive_metrics(store) -> Dict[str, Any]:
    """Get comprehensive parsing metrics for admin dashboard."""
    
    # Total A+ message analysis
    total_aplus_query = """
    SELECT COUNT(*) as total_aplus_messages
    FROM discord_messages dm 
    WHERE dm.content LIKE '%A+ Scalp Trade Setups%'
    """
    
    # Parsed A+ messages
    parsed_aplus_query = """
    SELECT COUNT(DISTINCT ts.message_id) as parsed_aplus_messages
    FROM trade_setups ts
    """
    
    # Messages by day with timezone conversion
    messages_by_day_query = """
    SELECT DATE(dm.timestamp AT TIME ZONE 'America/Chicago') as message_date,
           COUNT(*) as message_count,
           COUNT(CASE WHEN dm.content LIKE '%A+ Scalp Trade Setups%' THEN 1 END) as aplus_count,
           COUNT(CASE WHEN ts.message_id IS NOT NULL THEN 1 END) as parsed_count
    FROM discord_messages dm
    LEFT JOIN trade_setups ts ON dm.message_id = ts.message_id
    GROUP BY DATE(dm.timestamp AT TIME ZONE 'America/Chicago')
    ORDER BY message_date DESC
    LIMIT 10
    """
    
    # Weekend header analysis
    weekend_headers_query = """
    SELECT dm.message_id,
           dm.content,
           SPLIT_PART(dm.content, E'\n', 1) as header_line,
           dm.timestamp,
           EXTRACT(DOW FROM dm.timestamp AT TIME ZONE 'America/Chicago') as dow_central
    FROM discord_messages dm
    WHERE dm.content LIKE '%A+ Scalp Trade Setups%'
      AND (dm.content ILIKE '%sunday%' OR dm.content ILIKE '%saturday%')
    """
    
    # Parse failure analysis
    unparsed_analysis_query = """
    SELECT dm.message_id,
           LENGTH(dm.content) as content_length,
           SPLIT_PART(dm.content, E'\n', 1) as first_line,
           dm.timestamp
    FROM discord_messages dm 
    WHERE dm.content LIKE '%A+ Scalp Trade Setups%' 
      AND dm.message_id NOT IN (SELECT DISTINCT message_id FROM trade_setups WHERE message_id IS NOT NULL)
    ORDER BY dm.timestamp DESC
    """
    
    # Data quality metrics
    duplicate_setups_query = """
    SELECT message_id, COUNT(*) as setup_count
    FROM trade_setups 
    GROUP BY message_id 
    HAVING COUNT(*) > 1
    ORDER BY setup_count DESC
    """
    
    try:
        # Execute queries
        total_aplus = store.session.execute(text(total_aplus_query)).scalar() or 0
        parsed_aplus = store.session.execute(text(parsed_aplus_query)).scalar() or 0
        
        messages_by_day = [dict(row._mapping) for row in store.session.execute(text(messages_by_day_query)).fetchall()]
        weekend_headers = [dict(row._mapping) for row in store.session.execute(text(weekend_headers_query)).fetchall()]
        unparsed_analysis = [dict(row._mapping) for row in store.session.execute(text(unparsed_analysis_query)).fetchall()]
        duplicate_setups = [dict(row._mapping) for row in store.session.execute(text(duplicate_setups_query)).fetchall()]
        
        # Calculate derived metrics
        unparsed_count = total_aplus - parsed_aplus
        parsing_accuracy = (parsed_aplus / total_aplus * 100) if total_aplus > 0 else 0
        
        # Weekend setup detection
        weekend_setup_count_query = """
        SELECT COUNT(*) as weekend_setups
        FROM trade_setups ts
        WHERE ts.active = true 
          AND EXTRACT(DOW FROM ts.trading_day) IN (0, 6)
        """
        weekend_setups = store.session.execute(text(weekend_setup_count_query)).scalar() or 0
        
        return {
            'summary': {
                'total_aplus_messages': total_aplus,
                'parsed_aplus_messages': parsed_aplus,
                'unparsed_aplus_messages': unparsed_count,
                'parsing_accuracy_percent': round(parsing_accuracy, 1),
                'weekend_setups_detected': weekend_setups
            },
            'daily_breakdown': messages_by_day,
            'weekend_header_analysis': weekend_headers,
            'unparsed_message_analysis': unparsed_analysis,
            'data_quality': {
                'duplicate_message_groups': len(duplicate_setups),
                'duplicate_setups': duplicate_setups[:10]  # Top 10 duplicates
            },
            'recommendations': generate_recommendations(unparsed_count, weekend_setups, len(duplicate_setups))
        }
        
    except Exception as e:
        logger.error(f"Error executing comprehensive metrics queries: {e}")
        raise

def generate_recommendations(unparsed_count: int, weekend_setups: int, duplicate_count: int) -> List[str]:
    """Generate actionable recommendations based on metrics."""
    recommendations = []
    
    if unparsed_count > 0:
        recommendations.append(f"Review {unparsed_count} unparsed A+ messages for parsing errors or edge cases")
    
    if weekend_setups > 0:
        recommendations.append(f"Investigate {weekend_setups} weekend setups - check timezone conversion logic")
    
    if duplicate_count > 0:
        recommendations.append(f"Clean up {duplicate_count} duplicate setup groups to improve data quality")
    
    if unparsed_count == 0 and weekend_setups == 0:
        recommendations.append("Parsing system is operating optimally - consider automated regression testing")
    
    return recommendations