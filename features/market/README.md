# Market Feature

This module handles real-time market data monitoring and price triggers.

## Purpose

The market feature is responsible for:

1. Connecting to Alpaca WebSocket API to stream real-time price data
2. Maintaining a watchlist of symbols to monitor
3. Detecting when prices cross trigger levels defined in signals
4. Providing historical price data for analysis

## Components

### `price_monitor.py`

- Establishes and maintains WebSocket connections to Alpaca
- Processes real-time trade updates
- Checks for price triggers and publishes events when triggers are hit
- Manages the symbol watchlist

### `historical_data.py`

- Fetches historical price data for backtesting or analysis
- Supports various timeframes (minute, hour, day)
- Handles data caching to optimize API usage

## Inputs

- Signal price triggers from the strategy module
- Symbol list to monitor
- WebSocket data from Alpaca API

## Outputs

- Price trigger events published to Redis
- Current price data for dashboard display
- Historical price data for analysis

## Dependencies

- Alpaca API client for market data
- Redis for event publication
- WebSocket libraries for real-time streaming

## Testing

Tests for this feature focus on:
- WebSocket connection management
- Price trigger detection logic
- Historical data fetching and formatting

```
tests/
├── test_price_monitor.py
└── test_historical_data.py
```