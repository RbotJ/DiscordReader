"""
Historical Data Provider Module

This module provides historical market data for tracked symbols
and publishes candle updates using PostgreSQL events.
"""
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from common.db import db
from common.db_models import MarketDataModel
from common.events import publish_event, EventChannels
from features.alpaca.client import get_latest_bars, alpaca_market_client

# Configure logger
logger = logging.getLogger(__name__)

# Thread control variables
_data_thread = None
_thread_running = False

# Candle cache to avoid redundant updates
_candle_cache: Dict[str, Dict[str, Any]] = {}

def init_historical_data_provider() -> bool:
    """Initialize the historical data provider."""
    global _data_thread, _thread_running

    try:
        if not alpaca_market_client:
            logger.warning("Alpaca market client not initialized")
            return False

        if _data_thread and _data_thread.is_alive():
            logger.info("Historical data thread already running")
            return True

        _data_thread = threading.Thread(
            target=_historical_data_thread,
            daemon=True,
            name="HistoricalDataThread"
        )
        _thread_running = True
        _data_thread.start()

        time.sleep(0.1)

        if _data_thread.is_alive():
            logger.info("Historical data thread started successfully")
            return True
        else:
            logger.error("Historical data thread failed to start")
            return False
    except Exception as e:
        logger.error(f"Error initializing historical data provider: {e}")
        return False

def _historical_data_thread() -> None:
    """Historical data thread function."""
    global _thread_running

    logger.info("Historical data thread started")

    last_check = {
        '1Min': datetime.now() - timedelta(minutes=5),
        '5Min': datetime.now() - timedelta(minutes=20),
        '15Min': datetime.now() - timedelta(minutes=60),
        '1Hour': datetime.now() - timedelta(hours=4),
        '1Day': datetime.now() - timedelta(days=1)
    }

    while _thread_running:
        try:
            try:
                from features.market.price_monitor import get_monitored_symbols
                symbols = get_monitored_symbols()
            except ImportError:
                symbols = ["SPY", "AAPL", "MSFT", "NVDA", "TSLA"]

            if not symbols:
                time.sleep(10)
                continue

            now = datetime.now()

            if now - last_check['1Min'] >= timedelta(minutes=1):
                _update_candles(symbols, '1Min', 10)
                last_check['1Min'] = now

            if now - last_check['5Min'] >= timedelta(minutes=5):
                _update_candles(symbols, '5Min', 12)
                last_check['5Min'] = now

            if now - last_check['15Min'] >= timedelta(minutes=15):
                _update_candles(symbols, '15Min', 16)
                last_check['15Min'] = now

            if now - last_check['1Hour'] >= timedelta(hours=1):
                _update_candles(symbols, '1Hour', 24)
                last_check['1Hour'] = now

            if now - last_check['1Day'] >= timedelta(hours=6):
                _update_candles(symbols, '1Day', 30)
                last_check['1Day'] = now

            time.sleep(30)
        except Exception as e:
            logger.error(f"Error in historical data thread: {e}")
            time.sleep(60)

    logger.info("Historical data thread stopped")

def _update_candles(symbols: List[str], timeframe: str, limit: int) -> None:
    """Update candles for the given symbols and timeframe."""
    try:
        alpaca_timeframe = timeframe
        bars = get_latest_bars(symbols, alpaca_timeframe, limit)

        for symbol, symbol_bars in bars.items():
            if not symbol_bars:
                continue

            latest_candle = symbol_bars[-1]
            cache_key = f"{symbol}_{timeframe}"

            if (
                cache_key in _candle_cache and
                _candle_cache[cache_key].get('timestamp') == latest_candle.get('timestamp')
            ):
                continue

            _candle_cache[cache_key] = latest_candle

            # Store in database
            market_data = MarketDataModel(
                symbol=symbol,
                price=latest_candle.get('close'),
                previous_close=latest_candle.get('open'),
                volume=latest_candle.get('volume'),
                timestamp=datetime.fromisoformat(latest_candle.get('timestamp'))
            )

            try:
                db.session.add(market_data)
                db.session.commit()
            except Exception as e:
                logger.error(f"Error storing market data: {e}")
                db.session.rollback()
                continue

            # Publish event
            candle_update = {
                'ticker': symbol,
                'timeframe': timeframe,
                'timestamp': latest_candle.get('timestamp'),
                'open': latest_candle.get('open'),
                'high': latest_candle.get('high'),
                'low': latest_candle.get('low'),
                'close': latest_candle.get('close'),
                'volume': latest_candle.get('volume'),
                'event_type': 'candle_update',
                'is_closed': True
            }

            publish_event(
                event_type="market.bars.updated",
                data=candle_update,
                channel=EventChannels.MARKET_BARS_UPDATE,
                source="historical_data_provider"
            )

            logger.debug(f"Published {timeframe} candle update for {symbol}")
    except Exception as e:
        logger.error(f"Error updating {timeframe} candles: {e}")

def get_historical_data(symbol: str, timeframe: str = '1Day', limit: int = 30) -> List[Dict[str, Any]]:
    """Get historical data for a symbol."""
    try:
        bars = get_latest_bars([symbol], timeframe, limit)
        if symbol in bars:
            return bars[symbol]
        return []
    except Exception as e:
        logger.error(f"Error getting historical data for {symbol}: {e}")
        return []

def shutdown() -> bool:
    """Shutdown the historical data provider."""
    global _thread_running, _data_thread

    try:
        _thread_running = False

        if _data_thread and _data_thread.is_alive():
            _data_thread.join(timeout=5.0)

            if _data_thread.is_alive():
                logger.warning("Historical data thread did not stop gracefully")
                return False

        logger.info("Historical data provider shut down successfully")
        return True
    except Exception as e:
        logger.error(f"Error shutting down historical data provider: {e}")
        return False