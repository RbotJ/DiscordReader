# Setups Feature

This module handles the ingestion and parsing of trading setup messages.

## Purpose

The setups feature is responsible for:

1. Receiving raw A+ Setup messages from Discord, Email, or manual entry
2. Parsing these messages to extract actionable trading signals
3. Storing the parsed setups in the database
4. Publishing setup events to Redis for other components to consume

## Components

### `api.py`

Provides HTTP endpoints for:
- Receiving webhook callbacks from Discord/Email
- Manual entry of setup messages
- Retrieving stored setup messages

### `parser.py`

Contains the natural language processing logic to extract:
- Ticker symbols
- Signal types (breakout, breakdown, rejection, bounce)
- Price triggers
- Target levels
- Bias direction and conditions

## Inputs

- Raw text messages from Discord/Email webhooks
- Manual input through the web interface

## Outputs

- Parsed `TradeSetupMessage` objects stored in the database
- Setup events published to Redis channels
- API responses with parsed setup information

## Dependencies

- Redis for event publication
- PostgreSQL for persisting setup data
- Natural language processing utilities for parsing

## Testing

Tests for this feature focus on validating parsing logic with various message formats and ensuring proper event publication.

```
tests/
├── test_parser.py
└── test_api.py
```