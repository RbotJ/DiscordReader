# A+ Trading App

An advanced options trading platform that leverages cutting-edge technology to provide intelligent market insights, comprehensive trading analysis, and dynamic monitoring capabilities.

## Overview

The A+ Trading App is designed for traders who receive setup messages from Discord communities and want to automatically process and monitor trading signals. The application features:

- **Discord Bot Integration** - Real-time message monitoring with live metrics dashboard
- **Live Discord Monitoring** - In-memory message counting and trading alert detection
- **Operational Dashboard** - Real-time Discord bot status at `/dashboard/discord/`
- **Advanced Message Parsing** - AI-powered extraction of trading signals and setups
- **Enhanced Event System** - Complete operational telemetry with correlation tracking
- **Real-time Market Data** - Live ticker prices via Alpaca WebSocket integration
- **Interactive Dashboard** - Comprehensive monitoring with live event analytics
- **Correlation Flow Tracking** - End-to-end visibility from Discord messages to trade setups
- **Automated Cleanup** - 90-day retention policy with scheduled maintenance

## Architecture

The application follows a vertical-slice architecture, organized by features rather than layers. This approach maximizes separation of concerns while keeping related code together:

```
/  
├── features/
│   ├── dashboard/        # Interactive monitoring dashboard with event analytics
│   ├── discord_bot/      # Discord bot with live metrics, status tracking, and operational dashboard
│   │   ├── api.py        # Live metrics API endpoints (/api/discord/metrics)
│   │   ├── bot.py        # Core bot with in-memory message counting
│   │   ├── dashboard.py  # Real-time operational dashboard (/dashboard/discord/)
│   │   └── status_tracker.py # Connection status and health monitoring
│   ├── events/           # Enhanced PostgreSQL event bus with correlation tracking
│   ├── alpaca/           # WebSocket integration for real-time market data
│   ├── models/           # Database models organized by feature
│   │   └── new_schema/   # Enhanced schema (events, discord_channels, trade_setups, etc.)
│   ├── ingestion/        # Message processing and storage services
│   └── parsing/          # AI-powered setup extraction from Discord messages
├── common/
│   ├── db.py             # Enhanced database utilities with event publishing
│   ├── event_constants.py # Structured event channels and types
│   └── models.py         # Pydantic schemas and DTOs
├── docs/
│   ├── DATABASE_SCHEMA.md       # Complete database documentation
│   ├── PHASE_5_FUTURE_ENHANCEMENTS.md # Future development roadmap
│   └── architecture.md          # System architecture details
├── templates/            # Jinja2 templates for dashboard UI
├── static/               # CSS, JS, and assets for web interface
└── main.py              # Application entry point with enhanced initialization
```

Event orchestration is handled through an enhanced PostgreSQL-based event bus with correlation tracking, providing complete operational visibility from Discord messages through trade setup creation.

## Getting Started

### Prerequisites

- Python 3.8+
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

# Discord Bot Configuration
DISCORD_BOT_TOKEN=your_discord_bot_token

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

### Discord Bot Monitoring

Real-time Discord integration with operational visibility:
- **Live Message Counting** - In-memory tracking of daily message volume
- **Trading Alert Detection** - Automatic classification of trading-related messages using keyword matching
- **Real-time Dashboard** - Live operational metrics at `/dashboard/discord/` with 5-second refresh
- **Status Monitoring** - Connection health, latency tracking, and uptime metrics
- **Live Metrics API** - RESTful endpoint at `/api/discord/metrics` for integration
- **Database-Independent Operation** - Metrics persist in memory, unaffected by database issues

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
