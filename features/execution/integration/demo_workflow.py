import logging
from datetime import datetime
from common.events.publisher import publish_event, EventChannels
from common.db import db
from common.db_models import TradeModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def demo_trade_workflow():
    """Demonstrate trade workflow using PostgreSQL events"""
    try:
        # Create trade record
        trade = TradeModel(
            symbol="AAPL",
            quantity=100,
            price=150.00,
            timestamp=datetime.utcnow()
        )
        db.session.add(trade)
        db.session.commit()

        # Publish trade event
        publish_event(EventChannels.TRADE_EXECUTED, {
            "trade_id": trade.id,
            "symbol": trade.symbol,
            "quantity": trade.quantity,
            "price": trade.price
        })

        logger.info("Trade workflow completed successfully")
        return True
    except Exception as e:
        logger.error(f"Trade workflow failed: {e}")
        return False

if __name__ == "__main__":
    demo_trade_workflow()