"""
Common Utilities

Centralized utility functions to eliminate direct standard library imports
across slices and provide consistent utility patterns.
"""
import re
import asyncio
import threading
import schedule
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import asdict, is_dataclass
import json

logger = logging.getLogger(__name__)


class RegexUtils:
    """Regex utilities for consistent pattern matching."""
    
    @staticmethod
    def compile_pattern(pattern: str, flags: int = 0) -> re.Pattern:
        """Compile a regex pattern with error handling."""
        try:
            return re.compile(pattern, flags)
        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")
            raise ValueError(f"Invalid regex pattern: {e}")
    
    @staticmethod
    def search(pattern: Union[str, re.Pattern], text: str) -> Optional[re.Match]:
        """Search for a pattern in text."""
        if isinstance(pattern, str):
            pattern = RegexUtils.compile_pattern(pattern)
        return pattern.search(text)
    
    @staticmethod
    def find_all(pattern: Union[str, re.Pattern], text: str) -> List[str]:
        """Find all matches of a pattern in text."""
        if isinstance(pattern, str):
            pattern = RegexUtils.compile_pattern(pattern)
        return pattern.findall(text)
    
    @staticmethod
    def replace(pattern: Union[str, re.Pattern], replacement: str, text: str) -> str:
        """Replace pattern matches in text."""
        if isinstance(pattern, str):
            pattern = RegexUtils.compile_pattern(pattern)
        return pattern.sub(replacement, text)
    
    @staticmethod
    def split(pattern: Union[str, re.Pattern], text: str) -> List[str]:
        """Split text by pattern."""
        if isinstance(pattern, str):
            pattern = RegexUtils.compile_pattern(pattern)
        return pattern.split(text)


class AsyncUtils:
    """Async utilities for consistent async patterns."""
    
    @staticmethod
    def run_in_background(coro):
        """Run a coroutine in background without blocking."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                task = asyncio.create_task(coro)
                return task
            else:
                return asyncio.run(coro)
        except Exception as e:
            logger.error(f"Error running async task in background: {e}")
            return None
    
    @staticmethod
    async def run_with_timeout(coro, timeout: float):
        """Run a coroutine with timeout."""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Async operation timed out after {timeout} seconds")
            return None
    
    @staticmethod
    async def gather_with_errors(*coros, return_exceptions: bool = True):
        """Run multiple coroutines and handle errors gracefully."""
        try:
            results = await asyncio.gather(*coros, return_exceptions=return_exceptions)
            return results
        except Exception as e:
            logger.error(f"Error in async gather: {e}")
            return [None] * len(coros)
    
    @staticmethod
    def create_task_safe(coro, name: Optional[str] = None):
        """Create an async task with error handling."""
        try:
            task = asyncio.create_task(coro, name=name)
            
            def handle_task_exception(task):
                try:
                    task.result()
                except Exception as e:
                    logger.error(f"Unhandled exception in task {name or 'unnamed'}: {e}")
            
            task.add_done_callback(handle_task_exception)
            return task
        except Exception as e:
            logger.error(f"Error creating async task: {e}")
            return None


class ThreadingUtils:
    """Threading utilities for consistent threading patterns."""
    
    @staticmethod
    def run_in_thread(func: Callable, *args, daemon: bool = True, **kwargs):
        """Run a function in a separate thread."""
        try:
            thread = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=daemon)
            thread.start()
            return thread
        except Exception as e:
            logger.error(f"Error starting thread: {e}")
            return None
    
    @staticmethod
    def create_lock():
        """Create a thread lock."""
        return threading.Lock()
    
    @staticmethod
    def create_event():
        """Create a thread event."""
        return threading.Event()
    
    @staticmethod
    def create_condition():
        """Create a thread condition."""
        return threading.Condition()


class ScheduleUtils:
    """Schedule utilities for consistent job scheduling."""
    
    @staticmethod
    def schedule_every(interval: int, unit: str, func: Callable, *args, **kwargs):
        """Schedule a function to run at regular intervals."""
        try:
            job = getattr(schedule.every(interval), unit)
            job.do(func, *args, **kwargs)
            return job
        except Exception as e:
            logger.error(f"Error scheduling job: {e}")
            return None
    
    @staticmethod
    def schedule_at(time_str: str, func: Callable, *args, **kwargs):
        """Schedule a function to run at a specific time."""
        try:
            job = schedule.every().day.at(time_str)
            job.do(func, *args, **kwargs)
            return job
        except Exception as e:
            logger.error(f"Error scheduling timed job: {e}")
            return None
    
    @staticmethod
    def run_pending():
        """Run pending scheduled jobs."""
        try:
            schedule.run_pending()
        except Exception as e:
            logger.error(f"Error running pending jobs: {e}")
    
    @staticmethod
    def clear_all():
        """Clear all scheduled jobs."""
        schedule.clear()
    
    @staticmethod
    def cancel_job(job):
        """Cancel a scheduled job."""
        try:
            schedule.cancel_job(job)
        except Exception as e:
            logger.error(f"Error canceling job: {e}")


class DateTimeUtils:
    """DateTime utilities for consistent datetime handling."""
    
    @staticmethod
    def now_utc() -> datetime:
        """Get current UTC datetime."""
        return datetime.now(timezone.utc)
    
    @staticmethod
    def now_local() -> datetime:
        """Get current local datetime."""
        return datetime.now()
    
    @staticmethod
    def parse_iso(iso_string: str) -> Optional[datetime]:
        """Parse ISO format datetime string."""
        try:
            return datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        except ValueError as e:
            logger.error(f"Error parsing ISO datetime '{iso_string}': {e}")
            return None
    
    @staticmethod
    def to_iso(dt: datetime) -> str:
        """Convert datetime to ISO format string."""
        return dt.isoformat()
    
    @staticmethod
    def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Format datetime with custom format."""
        try:
            return dt.strftime(format_str)
        except Exception as e:
            logger.error(f"Error formatting datetime: {e}")
            return str(dt)


class DataUtils:
    """Data utilities for consistent data handling."""
    
    @staticmethod
    def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
        """Safely get value from dictionary."""
        return data.get(key, default) if isinstance(data, dict) else default
    
    @staticmethod
    def safe_int(value: Any, default: int = 0) -> int:
        """Safely convert value to integer."""
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def safe_float(value: Any, default: float = 0.0) -> float:
        """Safely convert value to float."""
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def safe_str(value: Any, default: str = "") -> str:
        """Safely convert value to string."""
        try:
            return str(value) if value is not None else default
        except Exception:
            return default
    
    @staticmethod
    def to_dict(obj: Any) -> Dict[str, Any]:
        """Convert object to dictionary."""
        if is_dataclass(obj):
            return asdict(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        elif isinstance(obj, dict):
            return obj
        else:
            return {}
    
    @staticmethod
    def to_json(obj: Any, pretty: bool = False) -> str:
        """Convert object to JSON string."""
        try:
            if is_dataclass(obj):
                obj = asdict(obj)
            
            if pretty:
                return json.dumps(obj, indent=2, default=str)
            else:
                return json.dumps(obj, default=str)
        except Exception as e:
            logger.error(f"Error converting to JSON: {e}")
            return "{}"
    
    @staticmethod
    def from_json(json_str: str) -> Any:
        """Parse JSON string to object."""
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON: {e}")
            return {}


class ValidationUtils:
    """Validation utilities for consistent validation patterns."""
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(RegexUtils.search(pattern, email))
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Validate URL format."""
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(RegexUtils.search(pattern, url))
    
    @staticmethod
    def is_valid_discord_id(discord_id: str) -> bool:
        """Validate Discord ID format."""
        pattern = r'^\d{17,19}$'
        return bool(RegexUtils.search(pattern, discord_id))
    
    @staticmethod
    def is_not_empty(value: Any) -> bool:
        """Check if value is not empty."""
        if value is None:
            return False
        if isinstance(value, str):
            return len(value.strip()) > 0
        if isinstance(value, (list, dict, tuple)):
            return len(value) > 0
        return True
    
    @staticmethod
    def is_within_length(value: str, min_length: int = 0, max_length: int = float('inf')) -> bool:
        """Check if string is within length bounds."""
        if not isinstance(value, str):
            return False
        return min_length <= len(value) <= max_length


class LoggingUtils:
    """Logging utilities for consistent logging patterns."""
    
    @staticmethod
    def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
        """Set up a logger with standard configuration."""
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper()))
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    @staticmethod
    def log_exception(logger: logging.Logger, message: str, exc: Exception):
        """Log an exception with context."""
        logger.error(f"{message}: {type(exc).__name__}: {exc}", exc_info=True)