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

from common.db import publish_event
from common.events import get_latest_events
from common.event_constants import EventChannels
from features.alpaca.client import get_latest_quote, alpaca_market_client
from common.event_compat import event_client
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
            logger.info("Price monitor started successfully")
            return True
        else:
            logger.error("Failed to start price monitor thread")
            return False

    except Exception as e:
        logger.error(f"Error initializing price monitor: {e}")
        return False

def _price_monitor_thread() -> None:
    """Background thread that monitors price updates for tracked symbols."""
    global _thread_running

    logger.info("Price monitor thread started")

    while _thread_running:
        try:
            if not _monitored_symbols:
                time.sleep(5)
                continue

            symbols = list(_monitored_symbols)

            for symbol in symbols:
                try:
                    quote = get_latest_quote([symbol])
                    if symbol not in quote or not quote[symbol]:
                        continue

                    symbol_quote = quote[symbol]
                    current_price = symbol_quote.get('close', symbol_quote.get('price', 0))
                    bid_price = symbol_quote.get('bid', 0)
                    ask_price = symbol_quote.get('ask', 0)
                    timestamp = datetime.utcnow()

                    # Cache the price update
                    update_price_cache(symbol, current_price, timestamp)

                    price_update = {
                        'ticker': symbol,
                        'price': current_price,
                        'bid_price': bid_price,
                        'ask_price': ask_price,
                        'timestamp': timestamp.isoformat(),
                        'event_type': 'price_update',
                        'status': 'active'
                    }

                    publish_event(
                        event_type="market.price.updated",
                        data=price_update,
                        channel=f"price:{symbol}",
                        source="price_monitor"
                    )
                    publish_event(
                        event_type="market.price.updated",
                        data=price_update,
                        channel=EventChannels.MARKET_PRICE_UPDATE,
                        source="price_monitor"
                    )

                except Exception as e:
                    logger.error(f"Error getting quote for {symbol}: {e}")

            time.sleep(1)
        except Exception as e:
            logger.error(f"Error in price monitor thread: {e}")
            time.sleep(5)

    logger.info("Price monitor thread stopped")

def add_symbol(symbol: str) -> bool:
    """Add a symbol to the price monitor."""
    try:
        _monitored_symbols.add(symbol.upper())

        watch_event = {
            'ticker': symbol.upper(),
            'event_type': 'watch',
            'timestamp': datetime.now().isoformat(),
            'status': 'active'
        }
        publish_event(
            event_type="market.symbol.watched",
            data=watch_event,
            channel=f"events:{symbol.upper()}",
            source="price_monitor"
        )
        publish_event(
            event_type="market.symbol.watched",
            data=watch_event,
            channel="events:all",
            source="price_monitor"
        )

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
    try:
        _monitored_symbols.discard(symbol.upper())

        unwatch_event = {
            'ticker': symbol.upper(),
            'event_type': 'unwatch',
            'timestamp': datetime.now().isoformat(),
            'status': 'inactive'
        }
        publish_event(
            event_type="market.symbol.unwatched",
            data=unwatch_event,
            channel=f"events:{symbol.upper()}",
            source="price_monitor"
        )
        publish_event(
            event_type="market.symbol.unwatched",
            data=unwatch_event,
            channel="events:all",
            source="price_monitor"
        )

        logger.info(f"Removed symbol from price monitor: {symbol}")
        return True
    except Exception as e:
        logger.error(f"Error removing symbol from price monitor: {e}")
        return False

def get_monitored_symbols() -> List[str]:
    """Get list of currently monitored symbols."""
    return list(_monitored_symbols)

def get_price(symbol: str) -> Optional[Dict[str, Any]]:
    """Get the latest cached price for a symbol."""
    return get_price_from_cache(symbol)

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

def publish_price_update(symbol: str, price: float, timestamp: datetime = None) -> bool:
    """Manually publish a price update event."""
    try:
        if timestamp is None:
            timestamp = datetime.utcnow()

        price_update = {
            'ticker': symbol.upper(),
            'price': price,
            'timestamp': timestamp.isoformat(),
            'event_type': 'price_update',
            'status': 'active'
        }

        publish_event(
            event_type="market.price.updated",
            data=price_update,
            channel=EventChannels.PRICE_UPDATE,
            source="price_monitor"
        )

        logger.debug(f"Published manual price update for {symbol}: {price}")
        return True
    except Exception as e:
        logger.error(f"Error publishing price update for {symbol}: {e}")
        return False