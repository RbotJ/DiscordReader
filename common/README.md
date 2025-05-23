# Common Components

This directory contains shared components and utilities used across multiple features in a vertical-slice architecture.

## Purpose

The `common/` module centralizes reusable logic, schemas, models, and helpers to ensure consistency across the application. It supports:

1. SQLAlchemy models for persistent entities
2. Dataclasses for DTOs and structured data exchange
3. Utility functions for logging, config, parsing, and formatting
4. Constants and enums for type-safe control flow
5. PostgreSQL-based event logging (no Redis)

## Components

### `models.py`
- Dataclasses for DTOs used in services and APIs
- Enums for typed data and trade classification

### `models_db.py`
- SQLAlchemy models for all core entities (setups, signals, trades, market data, etc.)
- Relationships and constraints for PostgreSQL schema

### `db.py`
- Singleton SQLAlchemy instance and initialization logic
- Raw query helper and DB connection checks
- PostgreSQL event logger (`publish_event`, `execute_query`)

### `utils.py`
- Logging setup and helpers
- Configuration loader from environment or file
- Price parsing and currency formatting
- Risk/reward calculator
- Unique ID generator for trade orders
- Setup level extraction for signal monitoring

### `constants.py`
- Market hours, position limits, risk defaults
- Core enums like `SignalState`, `TradeDirection`, `Timeframe`

### `event_channels.py`
- Flat constants for PostgreSQL event channel tagging

### `event_compat.py`
- Standardized interface for writing and querying events (used in logging/audit context)

## Usage

These modules are imported by vertical features like `setups/`, `strategy/`, and `execution/` to maintain consistency:

```python
from common.models import TradeSetupDTO, Signal, Bias
from common.models_db import SetupMessageModel, TradeModel
from common.utils import calculate_risk_reward, log_trade_execution
from common.db import publish_event
```

## Dependencies

- SQLAlchemy for ORM and database transactions
- Python dataclasses and enums for modeling
- JSON for serialization and audit logs
- Logging module for consistent output
- `os` and `uuid` for environment and ID generation

## Testing

Test coverage includes:
- DTO validation logic and enum integrity
- SQLAlchemy model relationships and constraints
- Utility function correctness and edge cases
- Event logging via PostgreSQL

```text
tests/
├── test_models.py
├── test_models_db.py
├── test_utils.py
└── test_event_logging.py