import logging
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from common.db import db
from common.db_models import TickerDataModel
from common.events import get_latest_events, EventChannels

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_active_tickers():
    """Get active tickers from database"""
    try:
        today = datetime.utcnow().date()
        ticker_data = TickerDataModel.query.filter(
            TickerDataModel.date >= today
        ).all()
        return [t.symbol for t in ticker_data]
    except Exception as e:
        logger.error(f"Error getting active tickers: {e}")
        return []

def main():
    st.title("Daily Active Tickers Dashboard")

    tickers = get_active_tickers()

    if not tickers:
        st.warning("No active tickers found for today")
        return

    st.write("Active Tickers Today:", len(tickers))
    st.write(pd.DataFrame({"Ticker": tickers}))

if __name__ == "__main__":
    main()