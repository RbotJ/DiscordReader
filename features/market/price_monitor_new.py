"""
Price Monitor Module

This module provides real-time price monitoring for tracked symbols
and publishes price updates using PostgreSQL-based event system.
"""
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Set, Any, Optional

from common.events.publisher import publish_event, get_latest_events
from common.events.constants import EventChannels
from features.alpaca.client import get_latest_quote, alpaca_market_client
from common.events import update_price_cache, get_price_from_cache

# Configure logger
logger = logging.getLogger(__name__)

# Thread control variables
_monitor_thread = None
_thread_running = False
_monitored_symbols: Set[str] = set()

def init_price_monitor() -> bool:
    """Initialize the price monitor."""
    global _monitor_thread, _thread_running

    try:
        if not alpaca_market_client:
            logger.warning("Alpaca market client not initialized")
            return False

        if _monitor_thread and _monitor_thread.is_alive():
            logger.info("Price monitor thread already running")
            return True

        _monitor_thread = threading.Thread(
            target=_price_monitor_thread,
            daemon=True,
            name="PriceMonitorThread"
        )
        _thread_running = True
        _monitor_thread.start()

        time.sleep(0.1)

        if _monitor_thread.is_alive():
            logger.info("Price monitor thread started successfully")
            return True
        else:
            logger.error("Failed to start price monitor thread")
            return False

    except Exception as e:
        logger.error(f"Error initializing price monitor: {e}")
        return False

def stop_price_monitor():
    """Stop the price monitor."""
    global _thread_running, _monitor_thread

    logger.info("Stopping price monitor...")
    _thread_running = False

    if _monitor_thread and _monitor_thread.is_alive():
        _monitor_thread.join(timeout=5.0)
        logger.info("Price monitor stopped")

def add_symbols(symbols: List[str]):
    """Add symbols to monitor."""
    global _monitored_symbols
    for symbol in symbols:
        _monitored_symbols.add(symbol.upper())
    logger.info(f"Added symbols to monitor: {symbols}")

def remove_symbols(symbols: List[str]):
    """Remove symbols from monitoring."""
    global _monitored_symbols
    for symbol in symbols:
        _monitored_symbols.discard(symbol.upper())
    logger.info(f"Removed symbols from monitor: {symbols}")

def get_monitored_symbols() -> Set[str]:
    """Get the current set of monitored symbols."""
    return _monitored_symbols.copy()

def _price_monitor_thread():
    """Main price monitoring thread."""
    logger.info("Price monitor thread started")
    
    while _thread_running:
        try:
            if not _monitored_symbols:
                time.sleep(1.0)
                continue

            for symbol in _monitored_symbols.copy():
                try:
                    quote = get_latest_quote(symbol)
                    if quote:
                        _process_price_update(symbol, quote)
                except Exception as e:
                    logger.error(f"Error processing price for {symbol}: {e}")

            time.sleep(0.5)  # Poll every 500ms

        except Exception as e:
            logger.error(f"Error in price monitor thread: {e}")
            time.sleep(1.0)

    logger.info("Price monitor thread exiting")

def _process_price_update(symbol: str, quote: Dict[str, Any]):
    """Process a price update for a symbol."""
    try:
        current_price = float(quote.get('askprice', 0) or quote.get('bidprice', 0))
        if current_price <= 0:
            return

        # Update price cache
        update_price_cache(symbol, current_price)

        # Publish price update event
        publish_event(
            event_type="market.price.updated",
            data={
                'symbol': symbol,
                'price': current_price,
                'bid': float(quote.get('bidprice', 0)),
                'ask': float(quote.get('askprice', 0)),
                'timestamp': datetime.utcnow().isoformat()
            },
            channel=EventChannels.TICKER_DATA,
            source="price_monitor"
        )

        logger.debug(f"Price update for {symbol}: ${current_price}")

    except Exception as e:
        logger.error(f"Error processing price update for {symbol}: {e}")

def get_current_price(symbol: str) -> Optional[float]:
    """Get the current cached price for a symbol."""
    return get_price_from_cache(symbol)

def is_monitor_running() -> bool:
    """Check if the price monitor is running."""
    return _thread_running and _monitor_thread and _monitor_thread.is_alive()

def get_monitor_status() -> Dict[str, Any]:
    """Get the current status of the price monitor."""
    return {
        'running': is_monitor_running(),
        'monitored_symbols': list(_monitored_symbols),
        'symbol_count': len(_monitored_symbols)
    }