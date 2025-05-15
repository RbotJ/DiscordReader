-- This file contains the schema for the A+ Trading App database
-- PostgreSQL compatible DDL statements

-- Enum types
CREATE TYPE signal_category_enum AS ENUM ('breakout', 'breakdown', 'rejection', 'bounce');
CREATE TYPE aggressiveness_enum AS ENUM ('none', 'low', 'medium', 'high');
CREATE TYPE comparison_type_enum AS ENUM ('above', 'below', 'near', 'range');
CREATE TYPE bias_direction_enum AS ENUM ('bullish', 'bearish');
CREATE TYPE order_side_enum AS ENUM ('buy', 'sell');
CREATE TYPE order_type_enum AS ENUM ('market', 'limit', 'stop', 'stop_limit');
CREATE TYPE order_status_enum AS ENUM ('new', 'filled', 'partially_filled', 'canceled', 'rejected');
CREATE TYPE time_in_force_enum AS ENUM ('day', 'gtc', 'ioc', 'fok');

-- Setup messages table
CREATE TABLE setup_messages (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    raw_text TEXT NOT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'unknown',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Ticker setups table
CREATE TABLE ticker_setups (
    id SERIAL PRIMARY KEY,
    setup_message_id INTEGER NOT NULL REFERENCES setup_messages(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_ticker_per_setup UNIQUE (setup_message_id, symbol)
);

-- Signals table
CREATE TABLE signals (
    id SERIAL PRIMARY KEY,
    ticker_setup_id INTEGER NOT NULL REFERENCES ticker_setups(id) ON DELETE CASCADE,
    category signal_category_enum NOT NULL,
    aggressiveness aggressiveness_enum NOT NULL DEFAULT 'none',
    comparison comparison_type_enum NOT NULL,
    trigger_price NUMERIC(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    triggered_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Signal targets table
CREATE TABLE signal_targets (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
    price NUMERIC(10, 2) NOT NULL,
    hit BOOLEAN NOT NULL DEFAULT FALSE,
    hit_at TIMESTAMP WITH TIME ZONE
);

-- Biases table
CREATE TABLE biases (
    id SERIAL PRIMARY KEY,
    ticker_setup_id INTEGER NOT NULL REFERENCES ticker_setups(id) ON DELETE CASCADE,
    direction bias_direction_enum NOT NULL,
    condition comparison_type_enum NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT one_bias_per_ticker_setup UNIQUE (ticker_setup_id)
);

-- Bias flips table
CREATE TABLE bias_flips (
    id SERIAL PRIMARY KEY,
    bias_id INTEGER NOT NULL REFERENCES biases(id) ON DELETE CASCADE,
    direction bias_direction_enum NOT NULL,
    price_level NUMERIC(10, 2) NOT NULL,
    triggered BOOLEAN NOT NULL DEFAULT FALSE,
    triggered_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT one_flip_per_bias UNIQUE (bias_id)
);

-- Market data table for price history
CREATE TABLE market_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    price NUMERIC(10, 4) NOT NULL,
    volume INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    
    CONSTRAINT unique_price_point UNIQUE (symbol, timestamp)
);

-- Orders table to track trades
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    client_order_id VARCHAR(50) UNIQUE,
    alpaca_order_id VARCHAR(50) UNIQUE,
    symbol VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL,
    side order_side_enum NOT NULL,
    type order_type_enum NOT NULL,
    time_in_force time_in_force_enum NOT NULL,
    limit_price NUMERIC(10, 2),
    stop_price NUMERIC(10, 2),
    status order_status_enum NOT NULL DEFAULT 'new',
    filled_quantity INTEGER DEFAULT 0,
    filled_price NUMERIC(10, 2),
    signal_id INTEGER REFERENCES signals(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Positions table
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL UNIQUE,
    quantity INTEGER NOT NULL,
    avg_entry_price NUMERIC(10, 2) NOT NULL,
    current_price NUMERIC(10, 2) NOT NULL,
    market_value NUMERIC(10, 2) NOT NULL,
    cost_basis NUMERIC(10, 2) NOT NULL,
    unrealized_pl NUMERIC(10, 2) NOT NULL,
    unrealized_plpc NUMERIC(10, 4) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Options contracts data cache
CREATE TABLE options_contracts (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL UNIQUE,
    underlying VARCHAR(20) NOT NULL,
    expiration_date DATE NOT NULL,
    strike NUMERIC(10, 2) NOT NULL,
    option_type VARCHAR(4) NOT NULL CHECK (option_type IN ('call', 'put')),
    bid NUMERIC(10, 2) NOT NULL,
    ask NUMERIC(10, 2) NOT NULL,
    last NUMERIC(10, 2),
    volume INTEGER,
    open_interest INTEGER,
    implied_volatility NUMERIC(10, 4),
    delta NUMERIC(10, 4),
    gamma NUMERIC(10, 4),
    theta NUMERIC(10, 4),
    vega NUMERIC(10, 4),
    rho NUMERIC(10, 4),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_option_contract UNIQUE (underlying, expiration_date, strike, option_type)
);

-- Index for efficient lookups
CREATE INDEX idx_setup_messages_date ON setup_messages(date);
CREATE INDEX idx_ticker_setups_symbol ON ticker_setups(symbol);
CREATE INDEX idx_signals_status ON signals(status);
CREATE INDEX idx_signals_category ON signals(category);
CREATE INDEX idx_market_data_symbol_timestamp ON market_data(symbol, timestamp);
CREATE INDEX idx_orders_symbol ON orders(symbol);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_options_contracts_underlying ON options_contracts(underlying);
CREATE INDEX idx_options_contracts_expiration ON options_contracts(expiration_date);

-- Views
CREATE VIEW active_signals AS
SELECT 
    s.id, 
    ts.symbol, 
    s.category, 
    s.comparison, 
    s.trigger_price, 
    s.status, 
    s.created_at,
    s.triggered_at,
    COUNT(st.id) AS target_count
FROM signals s
JOIN ticker_setups ts ON s.ticker_setup_id = ts.id
LEFT JOIN signal_targets st ON s.id = st.signal_id
WHERE s.status = 'pending'
GROUP BY s.id, ts.symbol;

CREATE VIEW triggered_signals AS
SELECT 
    s.id, 
    ts.symbol, 
    s.category, 
    s.comparison, 
    s.trigger_price, 
    s.status, 
    s.created_at,
    s.triggered_at,
    COUNT(o.id) AS order_count
FROM signals s
JOIN ticker_setups ts ON s.ticker_setup_id = ts.id
LEFT JOIN orders o ON s.id = o.signal_id
WHERE s.status = 'triggered'
GROUP BY s.id, ts.symbol;

-- Functions for signal management
CREATE OR REPLACE FUNCTION trigger_signal(signal_id INTEGER, trigger_price NUMERIC)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE signals
    SET status = 'triggered', 
        triggered_at = CURRENT_TIMESTAMP
    WHERE id = signal_id AND status = 'pending';
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Function to record a target hit
CREATE OR REPLACE FUNCTION hit_target(target_id INTEGER)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE signal_targets
    SET hit = TRUE, 
        hit_at = CURRENT_TIMESTAMP
    WHERE id = target_id AND hit = FALSE;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;
