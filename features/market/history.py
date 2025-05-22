"""
Market History Provider

This module provides access to historical market data from various sources.
"""
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Union

import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient, OptionHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, OptionBarsRequest
from alpaca.data.timeframe import TimeFrame

from common.db_models import TickerDataModel
from common.db import db_session
from features.alpaca.client import get_alpaca_api_key, get_alpaca_api_secret

logger = logging.getLogger(__name__)

# Global cache for history providers
_history_providers = {}

class HistoryProvider:
    """Base class for market data history providers."""
    
    def __init__(self, source: str = "alpaca"):
        """
        Initialize the history provider.
        
        Args:
            source: The data source to use
        """
        self.source = source
        
    def get_historical_data(self, ticker: str, 
                           start_date: Optional[date] = None,
                           end_date: Optional[date] = None,
                           timeframe: str = "1Day") -> pd.DataFrame:
        """
        Get historical data for a ticker.
        
        Args:
            ticker: The ticker symbol
            start_date: The start date for data retrieval
            end_date: The end date for data retrieval
            timeframe: The timeframe for the data ("1Day", "1Hour", etc.)
            
        Returns:
            DataFrame containing historical data
        """
        raise NotImplementedError("Subclasses must implement get_historical_data")


class AlpacaHistoryProvider(HistoryProvider):
    """Alpaca market data history provider."""
    
    def __init__(self):
        """Initialize the Alpaca history provider."""
        super().__init__(source="alpaca")
        self._stock_client = None
        self._option_client = None
        
    @property
    def stock_client(self) -> StockHistoricalDataClient:
        """Get the Alpaca stock historical data client."""
        if self._stock_client is None:
            try:
                api_key = get_alpaca_api_key()
                api_secret = get_alpaca_api_secret()
                self._stock_client = StockHistoricalDataClient(api_key, api_secret)
            except Exception as e:
                logger.error(f"Failed to initialize Alpaca stock client: {e}")
                raise
        return self._stock_client
    
    @property
    def option_client(self) -> OptionHistoricalDataClient:
        """Get the Alpaca option historical data client."""
        if self._option_client is None:
            try:
                api_key = get_alpaca_api_key()
                api_secret = get_alpaca_api_secret()
                self._option_client = OptionHistoricalDataClient(api_key, api_secret)
            except Exception as e:
                logger.error(f"Failed to initialize Alpaca option client: {e}")
                raise
        return self._option_client
        
    def get_historical_data(self, ticker: str, 
                           start_date: Optional[date] = None,
                           end_date: Optional[date] = None,
                           timeframe: str = "1Day") -> pd.DataFrame:
        """
        Get historical data for a ticker from Alpaca.
        
        Args:
            ticker: The ticker symbol
            start_date: The start date for data retrieval
            end_date: The end date for data retrieval
            timeframe: The timeframe for the data ("1Day", "1Hour", etc.)
            
        Returns:
            DataFrame containing historical data
        """
        # Default date range if not provided
        if start_date is None:
            start_date = date.today() - timedelta(days=30)
        if end_date is None:
            end_date = date.today()
            
        # Convert dates to datetime
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # Map timeframe string to Alpaca TimeFrame
        timeframe_map = {
            "1Day": TimeFrame.Day,
            "1Hour": TimeFrame.Hour,
            "15Min": TimeFrame.Minute,
            "5Min": TimeFrame.Minute,
            "1Min": TimeFrame.Minute
        }
        
        alpaca_timeframe = timeframe_map.get(timeframe, TimeFrame.Day)
        
        # Additional parameters for non-day timeframes
        timeframe_params = {}
        if timeframe == "15Min":
            timeframe_params["limit"] = 4 * 6.5 * 5  # ~4 bars per hour, 6.5 trading hours, 5 days
        elif timeframe == "5Min":
            timeframe_params["limit"] = 12 * 6.5 * 5  # ~12 bars per hour, 6.5 trading hours, 5 days
        elif timeframe == "1Min":
            timeframe_params["limit"] = 60 * 6.5 * 5  # ~60 bars per hour, 6.5 trading hours, 5 days
        
        try:
            # Create the request
            request = StockBarsRequest(
                symbol_or_symbols=ticker,
                timeframe=alpaca_timeframe,
                start=start_datetime,
                end=end_datetime,
                **timeframe_params
            )
            
            # Get the data
            bars = self.stock_client.get_stock_bars(request)
            
            # Convert to DataFrame
            if bars and ticker in bars:
                df = bars[ticker].df
                df.reset_index(inplace=True)
                df['date'] = df['timestamp'].dt.date
                return df
            else:
                logger.warning(f"No data returned for {ticker}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Failed to get historical data for {ticker}: {e}")
            return pd.DataFrame()


class DatabaseHistoryProvider(HistoryProvider):
    """Database market data history provider."""
    
    def __init__(self):
        """Initialize the database history provider."""
        super().__init__(source="database")
        
    def get_historical_data(self, ticker: str, 
                           start_date: Optional[date] = None,
                           end_date: Optional[date] = None,
                           timeframe: str = "1Day") -> pd.DataFrame:
        """
        Get historical data for a ticker from the database.
        
        Args:
            ticker: The ticker symbol
            start_date: The start date for data retrieval
            end_date: The end date for data retrieval
            timeframe: The timeframe for the data (only "1Day" supported)
            
        Returns:
            DataFrame containing historical data
        """
        # Database only supports daily data
        if timeframe != "1Day":
            logger.warning(f"Database only supports daily data, ignoring timeframe {timeframe}")
            
        # Default date range if not provided
        if start_date is None:
            start_date = date.today() - timedelta(days=30)
        if end_date is None:
            end_date = date.today()
            
        try:
            with db_session() as session:
                query = session.query(TickerDataModel).filter(
                    TickerDataModel.ticker == ticker,
                    TickerDataModel.date >= start_date,
                    TickerDataModel.date <= end_date
                ).order_by(TickerDataModel.date)
                
                results = query.all()
                
                if not results:
                    logger.warning(f"No data found in database for {ticker}")
                    return pd.DataFrame()
                    
                # Convert to DataFrame
                data = [{
                    'date': r.date,
                    'timestamp': datetime.combine(r.date, datetime.min.time()),
                    'open': r.open_price,
                    'high': r.high_price,
                    'low': r.low_price,
                    'close': r.close_price,
                    'volume': r.volume
                } for r in results]
                
                return pd.DataFrame(data)
                
        except Exception as e:
            logger.error(f"Failed to get historical data from database for {ticker}: {e}")
            return pd.DataFrame()


def get_history_provider(source: str = "alpaca") -> HistoryProvider:
    """
    Get a market data history provider.
    
    Args:
        source: The data source to use
        
    Returns:
        HistoryProvider instance
    """
    global _history_providers
    
    if source not in _history_providers:
        if source == "alpaca":
            _history_providers[source] = AlpacaHistoryProvider()
        elif source == "database":
            _history_providers[source] = DatabaseHistoryProvider()
        else:
            logger.error(f"Unknown history provider source: {source}")
            raise ValueError(f"Unknown history provider source: {source}")
            
    return _history_providers[source]