"""
Parsing Audit Module

Simple audit functionality that stays within parsing slice boundaries.
Uses only the parsing store's existing methods.
"""
import logging
from datetime import date
from typing import Dict, Any, List

from .store import get_parsing_store

logger = logging.getLogger(__name__)


class ParsingAudit:
    """Audit class for parsing data quality analysis within slice boundaries."""
    
    def __init__(self):
        self.store = get_parsing_store()
    
    def get_parsing_statistics_audit(self) -> Dict[str, Any]:
        """
        Get parsing statistics and basic audit information.
        Uses existing store methods only.
        """
        try:
            # Use existing store methods
            stats = self.store.get_parsing_statistics()
            
            return {
                'total_setups': stats.get('total_setups', 0),
                'active_setups': stats.get('active_setups', 0),
                'today_setups': stats.get('today_setups', 0),
                'total_levels': stats.get('total_levels', 0),
                'triggered_levels': stats.get('triggered_levels', 0),
                'setup_activation_rate': stats.get('setup_activation_rate', 0),
                'level_trigger_rate': stats.get('level_trigger_rate', 0),
                'audit_type': 'parsing_statistics'
            }
        except Exception as e:
            logger.error(f"Error in parsing statistics audit: {e}")
            return {'error': str(e), 'audit_type': 'parsing_statistics'}
    
    def get_trading_days_audit(self) -> Dict[str, Any]:
        """
        Get trading days distribution using existing store methods.
        """
        try:
            # Use existing store method
            trading_days = self.store.get_available_trading_days()
            
            return {
                'available_trading_days': trading_days,
                'unique_trading_days_count': len(trading_days) if trading_days else 0,
                'audit_type': 'trading_days'
            }
        except Exception as e:
            logger.error(f"Error in trading days audit: {e}")
            return {'error': str(e), 'audit_type': 'trading_days'}
    
    def get_comprehensive_audit_report(self) -> Dict[str, Any]:
        """Get comprehensive audit report using only parsing slice data."""
        return {
            'parsing_statistics': self.get_parsing_statistics_audit(),
            'trading_days': self.get_trading_days_audit(),
            'audit_timestamp': date.today().isoformat()
        }


# Global audit instance
_audit = None

def get_parsing_audit() -> ParsingAudit:
    """Get the global parsing audit instance."""
    global _audit
    if _audit is None:
        _audit = ParsingAudit()
    return _audit