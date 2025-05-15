# Common Components

This directory contains shared components and utilities used across multiple features.

## Purpose

The common components serve as the foundation for the application, providing:

1. Data models and schema definitions
2. Utility functions for common operations
3. Redis client for event orchestration
4. Shared configuration and constants

## Components

### `models.py`

- Pydantic models for data validation and serialization
- Enums for typed data consistency
- BaseModel extensions for common functionality
- Type annotations for improved code quality

### `redis_utils.py`

- Redis client wrapper for Pub/Sub operations
- JSON serialization helpers for complex objects
- Channel management for event orchestration
- Utility methods for common Redis operations

### `utils.py`

- Configuration loading and environment management
- Date and time formatting utilities
- Currency and number formatting functions
- Logging setup and helpers
- Risk/reward calculation utilities

### `constants.py`

- Channel names for Redis pub/sub
- Event type definitions
- Application-wide configuration defaults
- Status codes and error messages

## Usage

These common components are imported by the feature modules to provide consistent functionality across the application. For example:

```python
from common.models import Signal, TradeOrder, Position
from common.redis_utils import RedisClient
from common.utils import format_currency, calculate_risk_reward, log_trade_execution
```

## Dependencies

- Pydantic for data modeling and validation
- Redis for Pub/Sub and caching
- JSON for serialization
- Typing for type annotations

## Testing

Tests for these common components focus on:
- Model validation logic
- Redis client functionality
- Utility function correctness
- Serialization/deserialization accuracy

```
tests/
├── test_models.py
├── test_redis_utils.py
└── test_utils.py
```