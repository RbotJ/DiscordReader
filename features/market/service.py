"""
Market Data Service Layer

Centralized service for market data operations, providing a clean interface
for market status, quotes, candles, and real-time data without exposing
implementation details to API routes.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from features.market.history import get_history_provider
from features.market.feed import get_market_feed
from common.events.publisher import publish_event

logger = logging.getLogger(__name__)


@dataclass
class MarketStatusData:
    """Market status information."""
    is_open: bool
    next_open: Optional[datetime]
    next_close: Optional[datetime]
    session: str  # 'market', 'pre', 'post', 'closed'


@dataclass
class QuoteData:
    """Quote information for a symbol."""
    symbol: str
    bid: float
    ask: float
    last: float
    volume: int
    timestamp: datetime


@dataclass
class CandleData:
    """Candle/bar data."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class MarketService:
    """Service for market data operations."""
    
    def __init__(self):
        self.history_provider = None
        self.market_feed = None
        
    def _get_history_provider(self):
        """Lazy load history provider."""
        if not self.history_provider:
            self.history_provider = get_history_provider()
        return self.history_provider
        
    def _get_market_feed(self):
        """Lazy load market feed."""
        if not self.market_feed:
            self.market_feed = get_market_feed()
        return self.market_feed
    
    def get_market_status(self) -> MarketStatusData:
        """
        Get current market status.
        
        Returns:
            MarketStatusData with current market state
        """
        try:
            now = datetime.now()
            
            # Basic market hours logic (9:30 AM - 4:00 PM ET, Mon-Fri)
            is_weekday = now.weekday() < 5
            is_market_hours = 9.5 <= now.hour + now.minute/60 <= 16
            is_open = is_weekday and is_market_hours
            
            # Calculate next open/close times
            if is_open:
                # Market is open, next event is close at 4 PM
                next_close = datetime(now.year, now.month, now.day, 16, 0)
                next_open = None
                session = 'market'
            else:
                # Market is closed, calculate next open
                if now.hour >= 16 or not is_weekday:
                    # After hours or weekend
                    days_ahead = (7 - now.weekday()) % 7
                    if days_ahead == 0 and now.hour < 9.5:
                        # It's Monday before market open
                        next_open = datetime(now.year, now.month, now.day, 9, 30)
                    else:
                        next_day = now + timedelta(days=days_ahead if days_ahead > 0 else 1)
                        next_open = datetime(next_day.year, next_day.month, next_day.day, 9, 30)
                else:
                    # Before market open today
                    next_open = datetime(now.year, now.month, now.day, 9, 30)
                
                next_close = None
                
                # Determine session type
                if is_weekday and 4 <= now.hour < 9.5:
                    session = 'pre'
                elif is_weekday and 16 <= now.hour < 20:
                    session = 'post'
                else:
                    session = 'closed'
            
            status = MarketStatusData(
                is_open=is_open,
                next_open=next_open,
                next_close=next_close,
                session=session
            )
            
            # Publish market status event
            publish_event(
                event_type='market.status.retrieved',
                data={
                    'is_open': is_open,
                    'session': session,
                    'timestamp': now.isoformat()
                },
                channel='market:status',
                source='market_service'
            )
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting market status: {e}")
            # Return default closed status
            return MarketStatusData(
                is_open=False,
                next_open=None,
                next_close=None,
                session='closed'
            )
    
    def get_quote(self, symbol: str) -> Optional[QuoteData]:
        """
        Get the latest quote for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            QuoteData or None if not available
        """
        try:
            feed = self._get_market_feed()
            quote_data = feed.get_latest_quote(symbol)
            
            if not quote_data:
                logger.warning(f"No quote data available for {symbol}")
                return None
            
            quote = QuoteData(
                symbol=symbol.upper(),
                bid=quote_data.get('bid', 0.0),
                ask=quote_data.get('ask', 0.0),
                last=quote_data.get('last', 0.0),
                volume=quote_data.get('volume', 0),
                timestamp=datetime.now()
            )
            
            # Publish quote event
            publish_event(
                event_type='market.quote.retrieved',
                data={
                    'symbol': symbol.upper(),
                    'price': quote.last,
                    'timestamp': quote.timestamp.isoformat()
                },
                channel='market:quotes',
                source='market_service'
            )
            
            return quote
            
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            return None
    
    def get_candles(self, symbol: str, timeframe: str = '5m', 
                   start: Optional[str] = None, end: Optional[str] = None,
                   limit: int = 100) -> List[CandleData]:
        """
        Get candle/bar data for a symbol.
        
        Args:
            symbol: Stock symbol
            timeframe: Candle timeframe (e.g., '1m', '5m', '1h', '1d')
            start: Start date/time (ISO format)
            end: End date/time (ISO format)
            limit: Maximum number of candles
            
        Returns:
            List of CandleData
        """
        try:
            history = self._get_history_provider()
            raw_candles = history.get_candles(symbol, timeframe, start, end, limit)
            
            if not raw_candles:
                logger.warning(f"No candle data available for {symbol}")
                return []
            
            candles = []
            for candle in raw_candles:
                candle_data = CandleData(
                    symbol=symbol.upper(),
                    timestamp=datetime.fromisoformat(candle.get('timestamp', '')),
                    open=float(candle.get('open', 0)),
                    high=float(candle.get('high', 0)),
                    low=float(candle.get('low', 0)),
                    close=float(candle.get('close', 0)),
                    volume=int(candle.get('volume', 0))
                )
                candles.append(candle_data)
            
            # Publish candles event
            publish_event(
                event_type='market.candles.retrieved',
                data={
                    'symbol': symbol.upper(),
                    'timeframe': timeframe,
                    'count': len(candles),
                    'timestamp': datetime.now().isoformat()
                },
                channel='market:candles',
                source='market_service'
            )
            
            return candles
            
        except Exception as e:
            logger.error(f"Error getting candles for {symbol}: {e}")
            return []
    
    def subscribe_to_quotes(self, symbols: List[str]) -> bool:
        """
        Subscribe to real-time quote updates for symbols.
        
        Args:
            symbols: List of symbols to subscribe to
            
        Returns:
            True if subscription successful
        """
        try:
            feed = self._get_market_feed()
            success = feed.subscribe_quotes(symbols)
            
            if success:
                publish_event(
                    event_type='market.subscription.started',
                    data={
                        'symbols': symbols,
                        'timestamp': datetime.now().isoformat()
                    },
                    channel='market:subscriptions',
                    source='market_service'
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error subscribing to quotes: {e}")
            return False
    
    def unsubscribe_from_quotes(self, symbols: List[str]) -> bool:
        """
        Unsubscribe from real-time quote updates.
        
        Args:
            symbols: List of symbols to unsubscribe from
            
        Returns:
            True if unsubscription successful
        """
        try:
            feed = self._get_market_feed()
            success = feed.unsubscribe_quotes(symbols)
            
            if success:
                publish_event(
                    event_type='market.subscription.stopped',
                    data={
                        'symbols': symbols,
                        'timestamp': datetime.now().isoformat()
                    },
                    channel='market:subscriptions',
                    source='market_service'
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error unsubscribing from quotes: {e}")
            return False


# Global service instance
_market_service = None


def get_market_service() -> MarketService:
    """Get the market service instance."""
    global _market_service
    if _market_service is None:
        _market_service = MarketService()
    return _market_service