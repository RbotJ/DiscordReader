import logging
from flask import Blueprint, request, jsonify, render_template
from common.models import TradeSetupMessage, TickerSetup, Signal, Bias
from common.models import SignalCategory, ComparisonType, Aggressiveness
from .parser import parse_setup_message, get_stored_setups, add_manual_setup

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
setup_routes = Blueprint('setups', __name__)

@setup_routes.route('/api/setups', methods=['GET'])
def get_setups():
    """API endpoint to get all setups"""
    try:
        setups = get_stored_setups()
        # Convert to JSON-compatible format
        result = []
        for setup_msg in setups:
            result.append({
                "date": setup_msg.date.isoformat(),
                "raw_text": setup_msg.raw_text,
                "setups": [setup.dict() for setup in setup_msg.setups],
                "created_at": setup_msg.created_at.isoformat()
            })
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        logger.error(f"Error getting setups: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@setup_routes.route('/api/setups', methods=['POST'])
def create_setup():
    """API endpoint to create a new setup message"""
    try:
        data = request.json
        
        if "raw_text" in data:
            # Parse from raw text
            setup_message = parse_setup_message(data["raw_text"])
            if setup_message:
                return jsonify({
                    "status": "success", 
                    "message": "Setup parsed successfully",
                    "data": {
                        "ticker_count": len(setup_message.setups),
                        "tickers": [setup.symbol for setup in setup_message.setups]
                    }
                })
            else:
                return jsonify({"status": "error", "message": "Failed to parse setup message"}), 400
        elif "manual_setup" in data:
            # Create from structured data
            manual = data["manual_setup"]
            
            # Validate required fields
            if "symbol" not in manual or "signals" not in manual:
                return jsonify({"status": "error", "message": "Missing required fields"}), 400
            
            # Create signals
            signals = []
            for signal_data in manual["signals"]:
                try:
                    signal = Signal(
                        category=signal_data["category"],
                        comparison=signal_data["comparison"],
                        trigger=signal_data["trigger"],
                        targets=signal_data["targets"],
                        aggressiveness=signal_data.get("aggressiveness", Aggressiveness.NONE)
                    )
                    signals.append(signal)
                except Exception as e:
                    return jsonify({"status": "error", "message": f"Invalid signal: {str(e)}"}), 400
            
            # Create bias
            bias = None
            if "bias" in manual and manual["bias"]:
                try:
                    bias = Bias(
                        direction=manual["bias"]["direction"],
                        condition=manual["bias"]["condition"],
                        price=manual["bias"]["price"],
                        flip=manual["bias"].get("flip")
                    )
                except Exception as e:
                    return jsonify({"status": "error", "message": f"Invalid bias: {str(e)}"}), 400
            
            # Create ticker setup
            ticker_setup = TickerSetup(
                symbol=manual["symbol"],
                signals=signals,
                bias=bias
            )
            
            # Add to storage
            if add_manual_setup(ticker_setup):
                return jsonify({
                    "status": "success", 
                    "message": "Manual setup created successfully",
                    "data": {"ticker": ticker_setup.symbol}
                })
            else:
                return jsonify({"status": "error", "message": "Failed to store manual setup"}), 500
        else:
            return jsonify({"status": "error", "message": "Invalid request format"}), 400
            
    except Exception as e:
        logger.error(f"Error creating setup: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@setup_routes.route('/api/webhook/setup', methods=['POST'])
def setup_webhook():
    """Webhook endpoint for receiving setup messages from Discord/Email"""
    try:
        data = request.json
        
        # Extract message content based on source
        message_text = None
        
        if "content" in data:
            # Discord format
            message_text = data["content"]
        elif "body" in data:
            # Email format
            message_text = data["body"]
        elif "text" in data:
            # Generic format
            message_text = data["text"]
        
        if not message_text:
            return jsonify({"status": "error", "message": "No message content found"}), 400
        
        # Parse the message
        setup_message = parse_setup_message(message_text)
        
        if not setup_message:
            return jsonify({"status": "error", "message": "Failed to parse setup message"}), 400
        
        return jsonify({
            "status": "success", 
            "message": "Setup processed successfully",
            "data": {
                "ticker_count": len(setup_message.setups),
                "tickers": [setup.symbol for setup in setup_message.setups]
            }
        })
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
