# A+ Trading App Architecture

## Overview

The A+ Trading App follows a vertical-slice architecture, organizing code by feature rather than by layer. This approach maximizes separation of concerns while keeping related functionality together, making the codebase more maintainable and easier to navigate.

## Architecture Principles

Vertical Slices: Code is organized by feature rather than technical layer

Loose Coupling: Features communicate via PostgreSQL LISTEN/NOTIFY for event handling

High Cohesion: Related functionality is kept together

Single Responsibility: Each module has a clear, focused purpose

Event-Driven: Components communicate through DB-driven event channels

## Component Structure

```
/
├── features/
│   ├── ingestion/              # Ingest raw messages from Discord or other sources
│   │   ├── discord.py          # Discord API adapter
│   │   ├── fetcher.py          # Message pulling logic
│   │   ├── validator.py        # Pre-ingest validation
│   │   ├── service.py          # fetch → validate → store → notify orchestration
│   │   └── models.py           # DiscordMessageModel
│
│   ├── parsing/                # Parse raw messages into structured setups
│   │   ├── parser.py           # Regex/NLP parsing logic
│   │   ├── rules.py            # Aggressive/conservative long/short classification
│   │   ├── store.py            # SetupModel storage logic
│   │   ├── listener.py         # on MESSAGE_STORED → parse
│   │   └── models.py           # SetupModel
│
│   ├── market/                 # Price data feed & historical info
│   │   ├── feed.py             # Real-time websocket (Alpaca)
│   │   ├── history.py          # Candle data pull
│
│   ├── options_selector/       # Choose options contracts from setup signals
│   │   ├── chain_fetcher.py    # Retrieve option chains from Alpaca
│   │   ├── greeks.py           # Delta, theta, etc.
│   │   ├── filters.py          # Liquidity, IV, spreads
│   │   └── risk.py             # DTE rules, position sizing
│
│   ├── strategy/               # Signal logic & mapping to intent
│   │   ├── detector.py         # Detect price cross, volume surge, VWAP break
│   │   ├── selector.py         # Map signal → strategy → options contract
│   │   └── listener.py         # on SIGNAL_TRIGGERED → submit intent
│
│   ├── execution/              # Submit trades or simulate paper fills
│   │   ├── executor.py         # Alpaca trade submit
│   │   ├── simulator.py        # Paper trade emulator
│   │   └── listener.py         # on TRADE_INTENT → execute → notify
│
│   ├── management/             # Position tracking and automated exits
│   │   ├── positions.py        # Track open positions, Greeks, fill info
│   │   ├── exit_engine.py      # Stop loss / target logic
│   │   └── listener.py         # on TRADE_EXECUTED → monitor position
│
│   ├── notifications/          # Push alerts & updates to users
│   │   ├── discord.py          # Discord outbound
│   │   ├── slack.py            # Slack outbound
│   │   ├── listener.py         # on signal/position/update → notify
│   │   └── templates.py        # Alert templates for formatting
│
│   ├── dashboard/              # Data for visualization
│   │   ├── tickers.py          # Today's watchlist
│   │   ├── levels.py           # Support/resistance/targets
│   │   ├── ranges.py           # Ranges between levels
│   │   ├── listener.py         # Dashboard update trigger
│   │   └── api.py              # Streamlit/Flask endpoints
│
├── common/
│   ├── db.py                   # SQLAlchemy setup
│   ├── events.py               # Postgres LISTEN/NOTIFY event bus
│   ├── models.py               # Pydantic + DB models
│   ├── redis_utils.py          # Cache (optional)
│   └── utils.py                # Logging, config, shared helpers
│
├── templates/                  # Web UI HTML templates
├── static/                     # CSS, JS, assets
├── docs/                       # Architecture, schema, ADRs
│   ├── adr/
│   ├── schema.sql
│   └── architecture.md
└── app.py                      # Main entrypoint (Flask)


```

## Event Flow

The application uses PostgreSQL LISTEN/NOTIFY for inter-feature event orchestration:

MESSAGE_STORED - Raw message saved

SETUP_PARSED - Setup extracted from message

SIGNAL_TRIGGERED - Price action meets setup condition

TRADE_INTENT - Strategy chosen, trade planned

TRADE_EXECUTED - Trade submitted to broker

POSITION_UPDATED - Position opened or modified

POSITION_CLOSED - Exit rule met



This event-driven architecture allows components to be developed, tested, and deployed independently.

## Data Flow

The following diagram illustrates the data flow through the system:

```
[Discord] -> [Ingestion] --(MESSAGE_STORED)--> [Parsing] --(SETUP_PARSED)--> [Monitoring/Options/Dashboard]
                                                                |              ↘  [Dashboard]
                                                                v
                                                         [Notifications]
                                                                v
                                                         [Trade Execution] → [Alpaca API]
                                                                v
                                                       [Position Tracking]
```

Technologies

Python 3.8+: Core application language

Flask: Optional REST UI and endpoints

PostgreSQL: Primary database + event coordination

Alpaca API: Market data and trading

WebSockets: Real-time market stream

Bootstrap: UI framework for dashboards

Security Considerations

API Keys: Stored securely in environment variables

DB Access: Scoped roles for app-only access

Validation: All inputs validated and parsed before persistence

Rate Limiting: Internal limits and retries for external APIs

Deployment Architecture

Web Server: Hosts the UI, optional setup submission endpoint

Ingestion Worker: Pulls Discord messages

Parser Worker: Converts raw → setup

Strategy Worker: Tracks prices and fires triggers

Executor Worker: Submits trades

Management Worker: Tracks positions, applies exit logic

PostgreSQL: Central DB and event router

Future Enhancements

ML-enhanced setup classification and scoring

Replay system for setup re-simulation and backtesting

Full dashboard with trading journal and logs

Portfolio risk overlays

Mobile companion app

Development Roadmap

Phase 1: Message Ingest

Fetch Discord messages, store raw

Emit MESSAGE_STORED

Phase 2: Setup Parsing

Parse messages into setups

Emit SETUP_PARSED

Phase 3: Notifications + Dashboard

Send setup alerts

Update chart dashboards

Phase 4: Monitoring

Real-time monitoring of key levels

Trigger event on condition met

Phase 5: Option Selection + Trade Execution

Pick strike/contract

Submit paper trade

Phase 6: Position Tracking + Exit Logic

Track fills, stop/target rules

Notify on exit and update dashboard