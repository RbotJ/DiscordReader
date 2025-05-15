# Options Selector Feature

This module handles the selection of appropriate options contracts based on triggered signals.

## Purpose

The options selector feature is responsible for:

1. Fetching options chains for triggered signals
2. Calculating Greeks (Delta, Gamma, Theta, Vega) for options contracts
3. Filtering contracts based on predefined criteria
4. Selecting the optimal options contract for a given signal

## Components

### `chain_fetcher.py`

- Fetches options chain data from Alpaca API
- Caches chain data to minimize API calls
- Provides filtered views of the options chain

### `greeks_calculator.py`

- Calculates option Greeks using the Black-Scholes model
- Provides Delta ranges for bullish/bearish strategies
- Evaluates implied volatility levels

### `contract_filter.py`

- Filters options contracts based on:
  - Delta range (e.g., 0.3 to 0.7 for directional trades)
  - Volume/open interest thresholds
  - Spread width constraints
  - Days to expiration preferences

### `risk_assessor.py`

- Evaluates risk/reward profiles for potential options trades
- Recommends position sizing based on account size and risk parameters
- Calculates maximum risk for a given options contract

## Inputs

- Triggered signal data from the strategy module
- Current underlying price from the market module
- Risk parameters from configuration

## Outputs

- Selected options contracts for execution
- Greeks data for monitoring and dashboard display
- Risk assessment metrics

## Dependencies

- Alpaca API client for options chain data
- Mathematical libraries for Greeks calculations
- Strategy module for signal information
- Market module for underlying price data

## Testing

Tests for this feature focus on:
- Options chain fetching and caching
- Greeks calculation accuracy
- Contract filtering logic
- Risk assessment calculations

```
tests/
├── test_chain_fetcher.py
├── test_greeks_calculator.py
├── test_contract_filter.py
└── test_risk_assessor.py
```