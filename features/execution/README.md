# Execution Feature

This module handles the execution of options trades through the Alpaca API.

## Purpose

The execution feature is responsible for:

1. Placing options orders through Alpaca paper trading API
2. Tracking order status and handling errors
3. Managing position closures based on exit rules
4. Providing API endpoints for manual trading

## Components

### `executor.py`

- Establishes connection to Alpaca trading API
- Places buy/sell orders for options contracts
- Manages order lifecycle (submitted, filled, rejected)
- Handles partial position closing

### `paper_simulator.py`

- Simulates paper trading for options not available on Alpaca
- Calculates fill prices based on market data
- Tracks simulated positions and P&L

## Inputs

- Selected options contracts from the options_selector module
- Signal trigger events from the strategy module
- Manual trade instructions from the UI
- Position exit requests from management module

## Outputs

- Order status updates
- Position information
- Execution metrics and logs
- API responses for UI display

## Dependencies

- Alpaca API client for trade execution
- Redis for event subscription and publication
- Options selector module for contract selection
- Strategy module for signal information

## Testing

Tests for this feature focus on:
- Order placement accuracy
- Error handling and recovery
- Position tracking and management
- API endpoint functionality

```
tests/
├── test_executor.py
└── test_paper_simulator.py
```