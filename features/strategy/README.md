# Strategy Feature

This module handles the detection of trading opportunities based on price triggers.

## Purpose

The strategy feature is responsible for:

1. Subscribing to market price updates
2. Evaluating when a specific price trigger is hit
3. Converting price triggers into actionable trade signals
4. Managing active signals and their status

## Components

### `detector.py`

- Subscribes to market data channels via Redis
- Evaluates price conditions against signal triggers
- Generates trade signals when conditions are met
- Publishes trigger events for execution

### `signal_manager.py`

- Tracks active signals and their status
- Handles expiration and cancellation of signals
- Provides API endpoints for viewing and managing signals

## Inputs

- Parsed setup messages from the setups module
- Real-time price updates from the market module
- User commands to activate/deactivate strategies

## Outputs

- Signal trigger events published to Redis
- API responses with signal status information
- Logs of signal activations and executions

## Dependencies

- Redis for event subscription and publication
- Database for signal persistence
- Setups module for signal definitions
- Market module for price data

## Testing

Tests for this feature focus on:
- Trigger detection logic
- Signal activation under various market conditions
- Event publication correctness

```
tests/
├── test_detector.py
└── test_signal_manager.py
```