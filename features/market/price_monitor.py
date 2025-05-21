
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

from common.events import publish_event, EventChannels, update_price_cache, get_price_from_cache
from features.alpaca.client import get_latest_quote, alpaca_market_client

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
            logger.error("Price monitor thread failed to start")
            return False
    except Exception as e:
        logger.error(f"Error initializing price monitor: {e}")
        return False

def _price_monitor_thread() -> None:
    """Price monitor thread function."""
    global _thread_running

    logger.info("Price monitor thread started")

    while _thread_running:
        try:
            if not _monitored_symbols:
                time.sleep(1)
                continue

            for symbol in list(_monitored_symbols):
                try:
                    quote = get_latest_quote(symbol)

                    if not quote:
                        continue

                    timestamp = datetime.now()
                    bid_price = quote.get('bid_price')
                    ask_price = quote.get('ask_price')

                    if bid_price is not None and ask_price is not None:
                        price = (float(bid_price) + float(ask_price)) / 2
                    else:
                        price = quote.get('last_price', 0)

                    # Update price cache
                    update_price_cache(symbol, price, timestamp)

                    # Publish price update event
                    price_update = {
                        'ticker': symbol,
                        'price': price,
                        'bid_price': bid_price,
                        'ask_price': ask_price,
                        'timestamp': timestamp.isoformat(),
                        'event_type': 'price_update',
                        'status': 'active'
                    }

                    publish_event(f"price:{symbol}", price_update)
                    publish_event(EventChannels.MARKET_PRICE_UPDATE, price_update)

                except Exception as e:
                    logger.error(f"Error getting quote for {symbol}: {e}")

            time.sleep(1)
        except Exception as e:
            logger.error(f"Error in price monitor thread: {e}")
            time.sleep(5)

    logger.info("Price monitor thread stopped")

def add_symbol(symbol: str) -> bool:
    """Add a symbol to the price monitor."""
    global _monitored_symbols

    try:
        _monitored_symbols.add(symbol.upper())

        watch_event = {
            'ticker': symbol.upper(),
            'event_type': 'watch',
            'timestamp': datetime.now().isoformat(),
            'status': 'active'
        }
        publish_event(f"events:{symbol.upper()}", watch_event)
        publish_event("events:all", watch_event)

        logger.info(f"Added symbol to price monitor: {symbol}")
        return True
    except Exception as e:
        logger.error(f"Error adding symbol to price monitor: {e}")
        return False

def add_symbols(symbols: List[str]) -> bool:
    """Add multiple symbols to the price monitor."""
    try:
        for symbol in symbols:
            add_symbol(symbol)
        return True
    except Exception as e:
        logger.error(f"Error adding symbols to price monitor: {e}")
        return False

def remove_symbol(symbol: str) -> bool:
    """Remove a symbol from the price monitor."""
    global _monitored_symbols

    try:
        if symbol.upper() in _monitored_symbols:
            _monitored_symbols.remove(symbol.upper())

        unwatch_event = {
            'ticker': symbol.upper(),
            'event_type': 'unwatch',
            'timestamp': datetime.now().isoformat(),
            'status': 'inactive'
        }
        publish_event(f"events:{symbol.upper()}", unwatch_event)
        publish_event("events:all", unwatch_event)

        logger.info(f"Removed symbol from price monitor: {symbol}")
        return True
    except Exception as e:
        logger.error(f"Error removing symbol from price monitor: {e}")
        return False

def get_monitored_symbols() -> List[str]:
    """Get the list of currently monitored symbols."""
    return list(_monitored_symbols)

def shutdown() -> bool:
    """Shutdown the price monitor."""
    global _thread_running, _monitor_thread

    try:
        _thread_running = False

        if _monitor_thread and _monitor_thread.is_alive():
            _monitor_thread.join(timeout=5.0)

            if _monitor_thread.is_alive():
                logger.warning("Price monitor thread did not stop gracefully")
                return False

        logger.info("Price monitor shut down successfully")
        return True
    except Exception as e:
        logger.error(f"Error shutting down price monitor: {e}")
        return False
