# A+ Trading App

A sophisticated options trading application that automates the process of parsing trading signals, selecting appropriate options contracts, and executing paper trades through Alpaca API.

## Overview

The A+ Trading App is designed for traders who receive setup messages from various sources (like Discord or email) and want to automatically execute options trades based on those signals. The application features:

- Ingestion of setup messages through webhooks
- Advanced parsing of trading signals, targets, and biases
- Real-time market monitoring via Alpaca WebSocket
- Options chain fetching and Greek calculations
- Automated trade execution on signal triggers
- Position management and exit rules
- Web-based dashboard for monitoring activity

## Architecture

The application follows a vertical-slice architecture, organized by features rather than layers. This approach maximizes separation of concerns while keeping related code together:

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
│   ├── css/
│   └── js/
└── app.py               # Application entry point
```

Event orchestration between components is handled through Redis pub/sub, allowing for loose coupling between features.

## Getting Started

### Prerequisites

- Python 3.8+
- Redis server
- PostgreSQL database
- Alpaca Paper Trading account with API key and secret

### Environment Variables

The following environment variables should be set:

```
# Alpaca API Credentials
ALPACA_API_KEY=your_api_key
ALPACA_API_SECRET=your_api_secret
ALPACA_API_BASE_URL=https://paper-api.alpaca.markets

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/dbname

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Application Configuration
SESSION_SECRET=your_secret_key
```

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/aplus-trading-app.git
cd aplus-trading-app
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start the application:
```bash
python main.py
```

4. Access the web interface at http://localhost:5000

## Features

### Setup Message Parsing

Parses A+ setup messages, extracting:
- Ticker symbols
- Signal types (breakout, breakdown, rejection, bounce)
- Price triggers
- Target levels
- Bias information

### Market Data Monitoring

Connects to Alpaca WebSocket API to:
- Stream real-time price data for watchlist symbols
- Detect when prices cross trigger levels
- Update current position values

### Options Selection

- Fetches options chains for triggered signals
- Calculates Greeks (Delta, Gamma, Theta, Vega)
- Filters contracts based on Delta range, volume, spread
- Selects optimal contracts for bullish/bearish outlook

### Trade Execution

- Places options orders through Alpaca API
- Manages order lifecycle (submitted, filled, rejected)
- Supports market, limit, and stop orders
- Handles partial position closing

### Position Management

- Tracks open positions and P&L
- Applies exit rules based on profit targets or bias flips
- Manages risk through position sizing

## Development

### Project Structure

Each feature folder contains:
- `README.md` - Feature documentation
- Module files for the specific functionality
- Tests specific to that feature

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write or update tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
