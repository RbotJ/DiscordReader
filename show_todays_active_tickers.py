import logging
from datetime import datetime
from common.db import db
from common.db_models import TickerDataModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def show_active_tickers():
    """Display today's active tickers from database"""
    try:
        today = datetime.utcnow().date()
        tickers = TickerDataModel.query.filter(
            TickerDataModel.date >= today
        ).all()

        if not tickers:
            logger.info("No active tickers found for today")
            return

        for ticker in tickers:
            logger.info(f"Active ticker: {ticker.symbol}")

    except Exception as e:
        logger.error(f"Error showing active tickers: {e}")

if __name__ == "__main__":
    show_active_tickers()