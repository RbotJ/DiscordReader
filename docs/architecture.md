# A+ Trading App Architecture

## Overview

The A+ Trading App follows a vertical-slice architecture, organizing code by feature rather than by layer. This approach maximizes separation of concerns while keeping related functionality together, making the codebase more maintainable and easier to navigate.

## Architecture Principles

1. **Vertical Slices**: Code is organized by feature rather than technical layer
2. **Loose Coupling**: Features communicate via PostgreSQL events system
3. **High Cohesion**: Related functionality is kept together
4. **Single Responsibility**: Each module has a clear, focused purpose
5. **Event-Driven**: Components communicate via PostgreSQL for reliable event handling

## Component Structure

```
/
├── features/
│   ├── setups/           # ingestion, parsing, storage
│   ├── market/           # underlying price subscriptions
│   ├── options_selector/ # chain_fetcher, greeks, filters, risk
│   ├── strategy/         # detect triggers, map to signals
│   ├── execution/        # place orders, simulate
│   ├── management/       # positions, exit rules
│   └── notifications/    # Slack, dashboards
├── common/
│   ├── models.py         # Pydantic / SQLAlchemy definitions
│   └── utils.py          # logging, config loader
├── docs/
│   ├── adr/              # ADR Markdown files
│   ├── schema.sql        # relational schema
│   └── architecture.md   # detailed architecture docs
├── templates/            # HTML templates for web UI
├── static/               # CSS, JS, and assets for web UI
└── app.py                # Application entry point
```

## Event Flow

The application uses Redis pub/sub channels for event orchestration:

1. `setup.received` - Raw setup message received
2. `setup.parsed` - Setup has been parsed into signals
3. `market.price_update` - Real-time price update for a symbol
4. `signal.triggered` - A price trigger condition has been met
5. `trade.executed` - A trade has been executed
6. `position.updated` - A position has been updated
7. `position.closed` - A position has been closed

This event-driven architecture allows components to be developed, tested, and deployed independently.

## Data Flow

The following diagram illustrates the data flow through the system:

```
[Discord/Email] -> [Setups Parser] -> [Strategy Detector]
                                        |
[Alpaca WebSocket] -> [Price Monitor] --+
                                        |
                                        v
                                  [Options Selector]
                                        |
                                        v
                                  [Trade Executor] -> [Alpaca API]
                                        |
                                        v
                                  [Position Manager]
                                        |
                                        v
                                  [Notifications] -> [Slack/Email]
```

## Technologies

- **Python 3.8+**: Core application language
- **Flask**: Web framework for UI and API endpoints
- **Redis**: Event orchestration via pub/sub
- **PostgreSQL**: Persistent storage for setups, signals, and positions
- **Alpaca API**: Paper trading execution
- **WebSockets**: Real-time market data
- **Bootstrap**: UI components and styling

## Security Considerations

1. **API Keys**: Stored securely in environment variables
2. **Database Access**: Limited to application service account
3. **Input Validation**: All user input and webhook data is validated
4. **Rate Limiting**: API endpoints are rate-limited to prevent abuse

## Deployment Architecture

The application is designed to be deployed as a set of containerized services:

1. **Web Server**: Flask application with UI and API endpoints
2. **Market Watcher**: Process for WebSocket connections and price triggers
3. **Strategy Detector**: Process for evaluating signals against price data
4. **Executor**: Process for placing trades and managing positions
5. **Redis**: Message broker for event orchestration
6. **PostgreSQL**: Persistent storage

## Future Enhancements

1. **Machine Learning**: Add ML models for setup classification and signal quality scoring
2. **Historical Backtesting**: Allow backtesting of strategies against historical data
3. **Portfolio Optimization**: Add portfolio-level risk management and allocation
4. **Advanced Options Strategies**: Support for complex options strategies (spreads, etc.)
5. **Mobile App**: Companion mobile application for notifications and quick actions

## Development Process

The application follows a phased development approach:

**Phase 1: Core Infrastructure**
- Basic Flask application structure
- Database models and Redis client
- UI templates and static assets

**Phase 2: Setups and Signals**
- Setup parsing and storage
- Signal extraction and validation
- UI for viewing setups and signals

**Phase 3: Market Integration**
- Alpaca WebSocket integration
- Price monitoring and trigger detection
- Historical data fetching and display

**Phase 4: Options and Execution**
- Options chain fetching and filtering
- Greeks calculation and contract selection
- Trade execution via Alpaca API

**Phase 5: Position Management**
- Position tracking and display
- Exit rule implementation
- P&L calculation and visualization

**Phase 6: Notifications and Alerts**
- Slack and email integration
- Dashboard alerts and notifications
- Activity logging and reporting