"""
Market Historical Data Module

This module provides historical market data for charts and analysis.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from features.alpaca.client import get_stock_data_client, get_bars
from common.events import cache_data, get_from_cache

# Configure logger
logger = logging.getLogger(__name__)

def get_recent_candles(ticker: str, timeframe: str = '15Min', limit: int = 100) -> Optional[List[Dict]]:
    """
    Get recent candles for a ticker.

    Args:
        ticker: Ticker symbol
        timeframe: Candle timeframe (e.g., '1Min', '5Min', '15Min', '1Hour', '1Day')
        limit: Maximum number of candles to return

    Returns:
        List of candle dictionaries or None if data is not available
    """
    try:
        # Calculate start and end times
        end = datetime.now()

        # For daily candles, need more calendar days to get enough trading days
        if timeframe == '1Day':
            # Roughly 100 trading days is about 140 calendar days
            start = end - timedelta(days=limit * 1.4)
        else:
            # For intraday candles, factor in trading hours
            # A trading day is approximately 6.5 hours
            multiplier = 1  # Multiplier for timeframe conversion
            if timeframe == '1Min':
                multiplier = 1/60
            elif timeframe == '5Min':
                multiplier = 5/60
            elif timeframe == '15Min':
                multiplier = 15/60
            elif timeframe == '30Min':
                multiplier = 30/60
            elif timeframe == '1Hour':
                multiplier = 1

            trading_hours_needed = limit * multiplier
            calendar_days_needed = trading_hours_needed / 6.5

            # Add some buffer for holidays, weekends, etc.
            calendar_days_needed = calendar_days_needed * 1.5

            start = end - timedelta(days=max(1, calendar_days_needed))

        # Get candle data
        candles = get_bars(
            ticker,
            start=start,
            end=end,
            timeframe=timeframe,
            limit=limit
        )

        if not candles:
            logger.warning(f"No candle data returned for {ticker} with timeframe {timeframe}")
            return None

        # Format the candles for use in charts
        formatted_candles = []
        for candle in candles:
            formatted_candles.append({
                'time': candle.get('timestamp'),
                'open': candle.get('open'),
                'high': candle.get('high'),
                'low': candle.get('low'),
                'close': candle.get('close'),
                'volume': candle.get('volume')
            })

        return formatted_candles

    except Exception as e:
        logger.error(f"Error getting recent candles for {ticker}: {e}")
        return None

def get_candles_with_indicators(ticker: str, timeframe: str = '15Min', limit: int = 100) -> Optional[List[Dict]]:
    """
    Get recent candles with technical indicators for a ticker.

    Args:
        ticker: Ticker symbol
        timeframe: Candle timeframe (e.g., '1Min', '5Min', '15Min', '1Hour', '1Day')
        limit: Maximum number of candles to return

    Returns:
        List of candle dictionaries with indicators or None if data is not available
    """
    try:
        # Get raw candles
        candles = get_recent_candles(ticker, timeframe, limit)
        if not candles:
            return None

        # Add indicators
        for i in range(len(candles)):
            # Add EMA(9)
            ema9 = calculate_ema(candles, i, 9)
            candles[i]['ema9'] = ema9

            # Add EMA(20)
            ema20 = calculate_ema(candles, i, 20)
            candles[i]['ema20'] = ema20

            # Add VWAP (intraday only)
            if timeframe != '1Day':
                vwap = calculate_vwap(candles, i)
                candles[i]['vwap'] = vwap

        return candles

    except Exception as e:
        logger.error(f"Error adding indicators to candles for {ticker}: {e}")
        return None

def calculate_ema(candles: List[Dict], index: int, period: int) -> Optional[float]:
    """
    Calculate Exponential Moving Average.

    Args:
        candles: List of candle dictionaries
        index: Current index in the candles list
        period: EMA period

    Returns:
        EMA value or None if not enough data
    """
    # Need at least 'period' candles before the current one
    if index < period - 1:
        return None

    # Simple MA for the first value
    if index == period - 1:
        sma = sum(candle['close'] for candle in candles[:period]) / period
        return sma

    # Get previous EMA
    prev_ema = candles[index - 1].get('ema' + str(period))
    if prev_ema is None:
        return None

    # Calculate multiplier
    multiplier = 2 / (period + 1)

    # Calculate EMA
    ema = (candles[index]['close'] - prev_ema) * multiplier + prev_ema

    return ema

def calculate_vwap(candles: List[Dict], index: int) -> Optional[float]:
    """
    Calculate Volume-Weighted Average Price.

    Args:
        candles: List of candle dictionaries
        index: Current index in the candles list

    Returns:
        VWAP value or None if not enough data
    """
    # Need at least 1 candle
    if index < 0:
        return None

    # For simplicity, calculate VWAP for the day so far
    # In a real system, you would reset VWAP at market open

    # Get candles for today
    today_candles = candles[:index + 1]

    # Calculate sum of price * volume and sum of volume
    sum_pv = sum((c['high'] + c['low'] + c['close']) / 3 * c['volume'] for c in today_candles)
    sum_v = sum(c['volume'] for c in today_candles)

    if sum_v == 0:
        return None

    return sum_pv / sum_v