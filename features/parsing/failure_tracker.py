"""
Parsing Failure Tracker Module

Provides consolidated logging and tracking of parsing failures for analysis and debugging.
Stores failure reasons, message IDs, timestamps, and context for failed parsing attempts.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class FailureReason(Enum):
    """Enumeration of parsing failure reasons."""
    HEADER_MISSING = "header_missing"
    HEADER_INVALID = "header_invalid"
    CONTENT_TOO_SHORT = "content_too_short"
    TEST_INDICATOR = "test_indicator"
    PRICE_PARSE_FAILED = "price_parse_failed"
    NO_TICKER_SECTIONS = "no_ticker_sections"
    INVALID_DATE_FORMAT = "invalid_date_format"
    STRUCTURE_VALIDATION_FAILED = "structure_validation_failed"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ParseFailure:
    """Data class for storing parsing failure information."""
    message_id: str
    timestamp: datetime
    reason: FailureReason
    content_length: int
    first_line: str
    ticker_count: int
    error_details: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class FailureTracker:
    """
    Centralized tracking system for parsing failures.
    Provides in-memory storage and analysis capabilities.
    """
    
    def __init__(self):
        """Initialize failure tracker with empty storage."""
        self.failures: List[ParseFailure] = []
        self.max_failures = 1000  # Limit memory usage
        
    def record_failure(
        self, 
        message_id: str, 
        reason: FailureReason, 
        content: str = "",
        error_details: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a parsing failure for analysis.
        
        Args:
            message_id: Discord message ID
            reason: Reason for parsing failure
            content: Message content for analysis
            error_details: Specific error message or details
            context: Additional context information
        """
        try:
            # Extract analysis data from content
            lines = content.splitlines() if content else []
            first_line = lines[0][:100] if lines else ""
            
            # Count potential ticker sections (uppercase words alone on lines)
            ticker_count = 0
            for line in lines:
                line = line.strip()
                if len(line) >= 2 and len(line) <= 5 and line.isupper() and line.isalpha():
                    ticker_count += 1
            
            failure = ParseFailure(
                message_id=message_id,
                timestamp=datetime.utcnow(),
                reason=reason,
                content_length=len(content),
                first_line=first_line,
                ticker_count=ticker_count,
                error_details=error_details,
                context=context or {}
            )
            
            self.failures.append(failure)
            
            # Limit memory usage by removing oldest failures
            if len(self.failures) > self.max_failures:
                self.failures = self.failures[-self.max_failures:]
                
            logger.info(f"Recorded parsing failure for message {message_id}: {reason.value}")
            
        except Exception as e:
            logger.error(f"Error recording parsing failure: {e}")
    
    def get_failure_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics of parsing failures.
        
        Returns:
            Dictionary with failure analysis data
        """
        if not self.failures:
            return {
                'total_failures': 0,
                'recent_failures': 0,
                'failure_reasons': {},
                'average_content_length': 0
            }
        
        # Count failures by reason
        reason_counts = {}
        total_content_length = 0
        recent_failures = 0
        recent_threshold = datetime.utcnow().timestamp() - (24 * 60 * 60)  # 24 hours ago
        
        for failure in self.failures:
            reason_key = failure.reason.value
            reason_counts[reason_key] = reason_counts.get(reason_key, 0) + 1
            total_content_length += failure.content_length
            
            if failure.timestamp.timestamp() > recent_threshold:
                recent_failures += 1
        
        return {
            'total_failures': len(self.failures),
            'recent_failures': recent_failures,
            'failure_reasons': reason_counts,
            'average_content_length': round(total_content_length / len(self.failures), 1),
            'most_common_reason': max(reason_counts.items(), key=lambda x: x[1])[0] if reason_counts else None
        }
    
    def get_failures_by_reason(self, reason: FailureReason) -> List[ParseFailure]:
        """
        Get all failures for a specific reason.
        
        Args:
            reason: Failure reason to filter by
            
        Returns:
            List of failures matching the reason
        """
        return [f for f in self.failures if f.reason == reason]
    
    def get_recent_failures(self, hours: int = 24) -> List[ParseFailure]:
        """
        Get failures from the last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of recent failures
        """
        threshold = datetime.utcnow().timestamp() - (hours * 60 * 60)
        return [f for f in self.failures if f.timestamp.timestamp() > threshold]
    
    def export_failures(self) -> List[Dict[str, Any]]:
        """
        Export all failures as dictionaries for external analysis.
        
        Returns:
            List of failure dictionaries
        """
        return [asdict(failure) for failure in self.failures]
    
    def clear_failures(self) -> int:
        """
        Clear all stored failures.
        
        Returns:
            Number of failures that were cleared
        """
        count = len(self.failures)
        self.failures.clear()
        logger.info(f"Cleared {count} stored parsing failures")
        return count


# Global failure tracker instance
_failure_tracker = None


def get_failure_tracker() -> FailureTracker:
    """Get the global failure tracker instance."""
    global _failure_tracker
    if _failure_tracker is None:
        _failure_tracker = FailureTracker()
    return _failure_tracker


def record_parsing_failure(
    message_id: str,
    reason: FailureReason,
    content: str = "",
    error_details: Optional[str] = None,
    **context
) -> None:
    """
    Convenience function to record a parsing failure.
    
    Args:
        message_id: Discord message ID
        reason: Reason for parsing failure
        content: Message content for analysis
        error_details: Specific error message
        **context: Additional context as keyword arguments
    """
    tracker = get_failure_tracker()
    tracker.record_failure(message_id, reason, content, error_details, context)


def get_parsing_failure_summary() -> Dict[str, Any]:
    """
    Convenience function to get failure summary.
    
    Returns:
        Dictionary with failure analysis data
    """
    tracker = get_failure_tracker()
    return tracker.get_failure_summary()