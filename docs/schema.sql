-- A+ Trading App Database Schema

-- Setups Table
CREATE TABLE IF NOT EXISTS setups (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    raw_text TEXT NOT NULL,
    source VARCHAR(50) DEFAULT 'unknown',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Ticker Setups Table
CREATE TABLE IF NOT EXISTS ticker_setups (
    id SERIAL PRIMARY KEY,
    setup_id INTEGER REFERENCES setups(id) ON DELETE CASCADE,
    symbol VARCHAR(10) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Signals Table
CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    ticker_setup_id INTEGER REFERENCES ticker_setups(id) ON DELETE CASCADE,
    category VARCHAR(20) NOT NULL, -- breakout, breakdown, rejection, bounce
    aggressiveness VARCHAR(10) DEFAULT 'none', -- none, low, medium, high
    comparison VARCHAR(10) NOT NULL, -- above, below, near, range
    trigger_value JSONB NOT NULL, -- can be a single value or range
    targets JSONB NOT NULL, -- array of target price levels
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    triggered_at TIMESTAMP WITH TIME ZONE
);

-- Bias Table
CREATE TABLE IF NOT EXISTS biases (
    id SERIAL PRIMARY KEY,
    ticker_setup_id INTEGER REFERENCES ticker_setups(id) ON DELETE CASCADE,
    direction VARCHAR(10) NOT NULL, -- bullish, bearish
    condition VARCHAR(10) NOT NULL, -- above, below, near, range
    price NUMERIC(10, 2) NOT NULL,
    flip_direction VARCHAR(10), -- bullish, bearish
    flip_price_level NUMERIC(10, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Options Contracts Table
CREATE TABLE IF NOT EXISTS options_contracts (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    underlying VARCHAR(10) NOT NULL,
    expiration_date DATE NOT NULL,
    strike NUMERIC(10, 2) NOT NULL,
    option_type VARCHAR(4) NOT NULL, -- call, put
    last_update TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Current market data
    bid NUMERIC(10, 2),
    ask NUMERIC(10, 2),
    last NUMERIC(10, 2),
    volume INTEGER,
    open_interest INTEGER,
    -- Greeks
    implied_volatility NUMERIC(10, 4),
    delta NUMERIC(10, 4),
    gamma NUMERIC(10, 4),
    theta NUMERIC(10, 4),
    vega NUMERIC(10, 4),
    rho NUMERIC(10, 4)
);

-- Orders Table
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    alpaca_order_id VARCHAR(50),
    client_order_id VARCHAR(50) NOT NULL,
    signal_id INTEGER REFERENCES signals(id),
    symbol VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL,
    side VARCHAR(5) NOT NULL, -- buy, sell
    type VARCHAR(10) NOT NULL, -- market, limit, stop
    time_in_force VARCHAR(5) NOT NULL, -- day, gtc
    limit_price NUMERIC(10, 2),
    stop_price NUMERIC(10, 2),
    status VARCHAR(20) NOT NULL, -- submitted, filled, partial, canceled, rejected
    filled_qty INTEGER DEFAULT 0,
    filled_avg_price NUMERIC(10, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Positions Table
CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL,
    avg_entry_price NUMERIC(10, 2) NOT NULL,
    side VARCHAR(5) NOT NULL, -- long, short
    market_value NUMERIC(10, 2),
    cost_basis NUMERIC(10, 2),
    unrealized_pl NUMERIC(10, 2),
    unrealized_plpc NUMERIC(10, 4),
    current_price NUMERIC(10, 2),
    lastday_price NUMERIC(10, 2),
    change_today NUMERIC(10, 4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE
);

-- Price Triggers Table
CREATE TABLE IF NOT EXISTS price_triggers (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    comparison VARCHAR(10) NOT NULL, -- above, below, near, range
    trigger_value JSONB NOT NULL, -- single value or range
    signal_id INTEGER REFERENCES signals(id) ON DELETE CASCADE,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    triggered_at TIMESTAMP WITH TIME ZONE
);

-- Market Data Table
CREATE TABLE IF NOT EXISTS market_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    previous_close NUMERIC(10, 2),
    volume INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(symbol, timestamp)
);

-- Watchlist Table
CREATE TABLE IF NOT EXISTS watchlist (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL UNIQUE,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    type VARCHAR(20) NOT NULL, -- signal, trade, price, system
    title VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_signals_ticker_setup_id ON signals(ticker_setup_id);
CREATE INDEX IF NOT EXISTS idx_biases_ticker_setup_id ON biases(ticker_setup_id);
CREATE INDEX IF NOT EXISTS idx_options_contracts_underlying ON options_contracts(underlying);
CREATE INDEX IF NOT EXISTS idx_options_contracts_expiration ON options_contracts(expiration_date);
CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
CREATE INDEX IF NOT EXISTS idx_price_triggers_symbol ON price_triggers(symbol);
CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol);