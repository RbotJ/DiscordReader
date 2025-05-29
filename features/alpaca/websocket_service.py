"""
Alpaca WebSocket Service

Provides real-time ticker price updates via WebSocket connection to Alpaca.
Integrates with the enhanced event system for price alert monitoring.
"""
import logging
import json
import asyncio
import websockets
from typing import Dict, Any, Optional, List
from threading import Thread
import time
from datetime import datetime, time as dt_time
import pytz

from flask_socketio import emit
from common.events import EventChannels, EventTypes, publish_event_safe

logger = logging.getLogger(__name__)


class AlpacaWebSocketService:
    """Service for real-time ticker price streaming via Alpaca WebSocket."""
    
    def __init__(self, api_key: str, api_secret: str, paper_trading: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.paper_trading = paper_trading
        self.websocket = None
        self.running = False
        self.subscribed_tickers = set()
        self.last_prices = {}
        
        # Trading hours: 4:00 AM to 10:30 AM Eastern Time
        self.start_time = dt_time(4, 0)  # 4:00 AM
        self.end_time = dt_time(10, 30)   # 10:30 AM
        self.timezone = pytz.timezone('US/Eastern')
        
        # WebSocket URLs
        self.ws_url = "wss://stream.data.alpaca.markets/v2/iex" if not paper_trading else "wss://stream.data.alpaca.markets/v2/iex"
    
    def is_trading_hours(self) -> bool:
        """
        Check if current time is within trading hours (4:00 AM - 10:30 AM ET).
        
        Returns:
            bool: True if within trading hours, False otherwise
        """
        now_et = datetime.now(self.timezone)
        current_time = now_et.time()
        
        # Skip weekends
        if now_et.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        return self.start_time <= current_time <= self.end_time
    
    def start_price_streaming(self, tickers: List[str] = None):
        """
        Start WebSocket connection for real-time price streaming.
        Only runs during trading hours (4:00 AM - 10:30 AM ET).
        
        Args:
            tickers: List of ticker symbols to subscribe to
        """
        if self.running:
            logger.warning("Alpaca WebSocket service already running")
            return
        
        if not self.is_trading_hours():
            logger.info("Outside trading hours (4:00 AM - 10:30 AM ET). WebSocket will not start.")
            return
        
        self.running = True
        
        if tickers:
            self.subscribed_tickers.update(tickers)
        
        # Start WebSocket in separate thread
        self.ws_thread = Thread(target=self._run_websocket, daemon=True)
        self.ws_thread.start()
        
        logger.info(f"Alpaca WebSocket service started for tickers: {list(self.subscribed_tickers)}")
        
        # Publish startup event
        publish_event_safe(
            event_type=EventTypes.INFO,
            payload={
                'service': 'alpaca_websocket',
                'status': 'started',
                'subscribed_tickers': list(self.subscribed_tickers),
                'trading_hours': f"{self.start_time} - {self.end_time} ET"
            },
            channel=EventChannels.SYSTEM,
            source='alpaca_websocket_service'
        )
    
    def stop_price_streaming(self):
        """Stop WebSocket connection."""
        self.running = False
        
        if self.websocket:
            asyncio.create_task(self.websocket.close())
        
        logger.info("Alpaca WebSocket service stopped")
        
        # Publish shutdown event
        publish_event_safe(
            event_type=EventTypes.INFO,
            payload={
                'service': 'alpaca_websocket',
                'status': 'stopped'
            },
            channel=EventChannels.SYSTEM,
            source='alpaca_websocket_service'
        )
    
    def subscribe_ticker(self, ticker: str):
        """
        Subscribe to real-time updates for a specific ticker.
        
        Args:
            ticker: Ticker symbol to subscribe to
        """
        if ticker not in self.subscribed_tickers:
            self.subscribed_tickers.add(ticker)
            
            if self.websocket:
                asyncio.create_task(self._send_subscription(ticker))
            
            logger.info(f"Subscribed to ticker: {ticker}")
    
    def unsubscribe_ticker(self, ticker: str):
        """
        Unsubscribe from real-time updates for a specific ticker.
        
        Args:
            ticker: Ticker symbol to unsubscribe from
        """
        if ticker in self.subscribed_tickers:
            self.subscribed_tickers.remove(ticker)
            
            if self.websocket:
                asyncio.create_task(self._send_unsubscription(ticker))
            
            logger.info(f"Unsubscribed from ticker: {ticker}")
    
    def get_last_price(self, ticker: str) -> Optional[float]:
        """
        Get the last known price for a ticker.
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            Optional[float]: Last known price or None
        """
        return self.last_prices.get(ticker)
    
    def _run_websocket(self):
        """Run the WebSocket connection in an async loop."""
        try:
            asyncio.run(self._websocket_handler())
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            
            # Publish error event
            publish_event_safe(
                event_type=EventTypes.ERROR,
                payload={
                    'service': 'alpaca_websocket',
                    'error': str(e),
                    'action': 'connection_failed'
                },
                channel=EventChannels.SYSTEM,
                source='alpaca_websocket_service'
            )
    
    async def _websocket_handler(self):
        """Handle WebSocket connection and message processing."""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                self.websocket = websocket
                
                # Authenticate
                await self._authenticate()
                
                # Subscribe to tickers
                for ticker in self.subscribed_tickers:
                    await self._send_subscription(ticker)
                
                # Listen for messages with periodic time checks
                async for message in websocket:
                    # Check if we're still within trading hours
                    if not self.is_trading_hours():
                        logger.info("Trading hours ended (10:30 AM ET). Closing WebSocket connection.")
                        await websocket.close()
                        break
                    
                    await self._handle_message(message)
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            self.running = False
    
    async def _authenticate(self):
        """Authenticate with Alpaca WebSocket."""
        auth_message = {
            "action": "auth",
            "key": self.api_key,
            "secret": self.api_secret
        }
        
        await self.websocket.send(json.dumps(auth_message))
        logger.info("Sent authentication to Alpaca WebSocket")
    
    async def _send_subscription(self, ticker: str):
        """Send subscription message for a ticker."""
        sub_message = {
            "action": "subscribe",
            "trades": [ticker],
            "quotes": [ticker]
        }
        
        await self.websocket.send(json.dumps(sub_message))
        logger.info(f"Sent subscription for {ticker}")
    
    async def _send_unsubscription(self, ticker: str):
        """Send unsubscription message for a ticker."""
        unsub_message = {
            "action": "unsubscribe",
            "trades": [ticker],
            "quotes": [ticker]
        }
        
        await self.websocket.send(json.dumps(unsub_message))
        logger.info(f"Sent unsubscription for {ticker}")
    
    async def _handle_message(self, message: str):
        """
        Handle incoming WebSocket messages.
        
        Args:
            message: Raw WebSocket message
        """
        try:
            data = json.loads(message)
            
            if isinstance(data, list):
                for item in data:
                    await self._process_market_data(item)
            else:
                await self._process_market_data(data)
                
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing WebSocket message: {e}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
    
    async def _process_market_data(self, data: Dict[str, Any]):
        """
        Process market data and emit to dashboard clients.
        
        Args:
            data: Market data item
        """
        try:
            # Handle trade data
            if data.get('T') == 't':  # Trade message
                ticker = data.get('S')
                price = data.get('p')
                
                if ticker and price:
                    self.last_prices[ticker] = price
                    
                    # Emit to dashboard via SocketIO
                    from app import socketio
                    socketio.emit('ticker_update', {
                        'ticker': ticker,
                        'price': price,
                        'timestamp': data.get('t'),
                        'volume': data.get('s')
                    })
                    
                    # Publish price update event
                    publish_event_safe(
                        event_type=EventTypes.TICKER_DATA,
                        payload={
                            'ticker': ticker,
                            'price': price,
                            'volume': data.get('s', 0),
                            'timestamp': data.get('t')
                        },
                        channel=EventChannels.TICKER_DATA,
                        source='alpaca_websocket'
                    )
            
            # Handle quote data
            elif data.get('T') == 'q':  # Quote message
                ticker = data.get('S')
                bid_price = data.get('bp')
                ask_price = data.get('ap')
                
                if ticker and (bid_price or ask_price):
                    # Emit quote to dashboard
                    from app import socketio
                    socketio.emit('quote_update', {
                        'ticker': ticker,
                        'bid_price': bid_price,
                        'ask_price': ask_price,
                        'timestamp': data.get('t')
                    })
                    
        except Exception as e:
            logger.error(f"Error processing market data: {e}")


# Global WebSocket service instance
websocket_service = None

def initialize_websocket_service(api_key: str, api_secret: str, paper_trading: bool = True):
    """
    Initialize the global WebSocket service.
    
    Args:
        api_key: Alpaca API key
        api_secret: Alpaca API secret
        paper_trading: Whether to use paper trading endpoint
    """
    global websocket_service
    
    if not api_key or not api_secret:
        logger.warning("Alpaca API credentials not provided - WebSocket service disabled")
        return None
    
    websocket_service = AlpacaWebSocketService(api_key, api_secret, paper_trading)
    return websocket_service

def get_websocket_service() -> Optional[AlpacaWebSocketService]:
    """Get the global WebSocket service instance."""
    return websocket_service