#!/bin/bash

echo "Starting Daily Trading Ticker Dashboard..."
streamlit run daily_ticker_dashboard.py --server.port=8504 --server.address=0.0.0.0