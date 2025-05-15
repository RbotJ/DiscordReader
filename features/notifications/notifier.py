import logging
import json
import threading
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional

from common.utils import publish_event, subscribe_to_channel, load_config

# Configure logging
logger = logging.getLogger(__name__)

# In-memory notification storage
_notifications: List[Dict[str, Any]] = []

def start_notification_listener() -> bool:
    """Start listening for events to send notifications"""
    try:
        # Subscribe to various event channels
        subscribe_to_channel("execution.order_submitted", _on_order_submitted)
        subscribe_to_channel("execution.order_filled", _on_order_filled)
        subscribe_to_channel("execution.order_canceled", _on_order_canceled)
        subscribe_to_channel("execution.order_error", _on_order_error)
        subscribe_to_channel("position.opened", _on_position_opened)
        subscribe_to_channel("position.closed", _on_position_closed)
        subscribe_to_channel("strategy.signal_triggered", _on_signal_triggered)
        
        logger.info("Notification listener started")
        return True
    except Exception as e:
        logger.error(f"Failed to start notification listener: {str(e)}")
        return False

def _on_order_submitted(data: Dict) -> None:
    """Handle order submitted event"""
    symbol = data.get("symbol", "")
    side = data.get("side", "")
    quantity = data.get("quantity", 0)
    
    message = f"Order submitted: {side.upper()} {quantity} {symbol}"
    
    # Add option details if present
    if data.get("option_symbol"):
        message += f" (option: {data['option_symbol']})"
    
    send_notification(message, data=data)

def _on_order_filled(data: Dict) -> None:
    """Handle order filled event"""
    symbol = data.get("symbol", "")
    side = data.get("side", "")
    quantity = data.get("quantity", 0)
    price = data.get("filled_price", 0)
    
    message = f"Order filled: {side.upper()} {quantity} {symbol} @ {price}"
    
    # Add option details if present
    if data.get("option_symbol"):
        message += f" (option: {data['option_symbol']})"
    
    send_notification(message, level="success", data=data)

def _on_order_canceled(data: Dict) -> None:
    """Handle order canceled event"""
    symbol = data.get("symbol", "")
    
    message = f"Order canceled: {symbol}"
    
    # Add option details if present
    if data.get("option_symbol"):
        message += f" (option: {data['option_symbol']})"
    
    send_notification(message, level="warning", data=data)

def _on_order_error(data: Dict) -> None:
    """Handle order error event"""
    symbol = data.get("symbol", "")
    error = data.get("error", "Unknown error")
    
    message = f"Order error for {symbol}: {error}"
    
    send_notification(message, level="error", data=data)

def _on_position_opened(data: Dict) -> None:
    """Handle position opened event"""
    symbol = data.get("symbol", "")
    side = data.get("side", "")
    quantity = data.get("quantity", 0)
    price = data.get("average_price", 0)
    
    message = f"Position opened: {side.upper()} {quantity} {symbol} @ {price}"
    
    # Add option details if present
    if data.get("option_symbol"):
        message += f" (option: {data['option_symbol']})"
    
    # Add strategy if present
    if data.get("strategy"):
        message += f" [{data['strategy']}]"
    
    send_notification(message, level="success", data=data)

def _on_position_closed(data: Dict) -> None:
    """Handle position closed event"""
    symbol = data.get("symbol", "")
    pl = data.get("pl", 0)
    pl_percent = data.get("pl_percent", 0)
    exit_reason = data.get("exit_reason", "unknown")
    
    # Format P/L with color indicator
    pl_sign = "+" if pl > 0 else ""
    message = f"Position closed: {symbol} with {pl_sign}{pl:.2f} ({pl_sign}{pl_percent:.2f}%) [{exit_reason}]"
    
    # Add option details if present
    if data.get("option_symbol"):
        message += f" (option: {data['option_symbol']})"
    
    # Set level based on P/L
    level = "success" if pl > 0 else "warning"
    
    send_notification(message, level=level, data=data)

def _on_signal_triggered(data: Dict) -> None:
    """Handle signal triggered event"""
    symbol = data.get("symbol", "")
    price = data.get("price", 0)
    
    if data.get("manual", False):
        signal_type = data.get("signal_type", "unknown")
        message = f"Manual signal triggered: {symbol} {signal_type} @ {price}"
    else:
        # Get signal categories
        signal_categories = []
        for signal in data.get("signals", []):
            if "category" in signal:
                signal_categories.append(signal["category"])
        
        category_str = ", ".join(signal_categories) if signal_categories else "unknown"
        message = f"Signal triggered: {symbol} {category_str} @ {price}"
    
    send_notification(message, data=data)

def send_notification(message: str, level: str = "info", data: Optional[Dict] = None) -> bool:
    """
    Send a notification
    
    Args:
        message: Notification message text
        level: Notification level ('info', 'success', 'warning', 'error')
        data: Optional data to include with notification
    
    Returns:
        True if notification was sent successfully
    """
    try:
        # Create notification object
        notification = {
            "message": message,
            "level": level,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        # Store in memory
        _notifications.append(notification)
        
        # Limit stored notifications
        if len(_notifications) > 100:
            _notifications.pop(0)
        
        # Log notification
        log_level = getattr(logging, level.upper(), logging.INFO)
        logger.log(log_level, f"Notification: {message}")
        
        # Send to webhook if configured
        _send_to_webhook(notification)
        
        return True
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")
        return False

def _send_to_webhook(notification: Dict) -> None:
    """Send notification to configured webhook"""
    try:
        # Load config
        config = load_config()
        webhook_url = config['settings']['notification_webhook']
        
        # Skip if no webhook configured
        if not webhook_url:
            return
        
        # Send in a separate thread to avoid blocking
        thread = threading.Thread(target=_send_webhook_request, args=(webhook_url, notification))
        thread.daemon = True
        thread.start()
    
    except Exception as e:
        logger.error(f"Error preparing webhook: {str(e)}")

def _send_webhook_request(webhook_url: str, notification: Dict) -> None:
    """Send the actual webhook request"""
    try:
        # Create payload
        payload = {
            "text": notification["message"],
            "level": notification["level"],
            "timestamp": notification["timestamp"]
        }
        
        # Add optional data if not too large
        if notification.get("data") and len(json.dumps(notification["data"])) < 1000:
            payload["data"] = notification["data"]
        
        # Send request
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        
        # Check response
        if response.status_code >= 400:
            logger.warning(f"Webhook request failed: {response.status_code} - {response.text}")
    
    except Exception as e:
        logger.error(f"Error sending webhook request: {str(e)}")

def get_notifications(limit: int = 20) -> List[Dict]:
    """
    Get recent notifications
    
    Args:
        limit: Maximum number of notifications to return
    
    Returns:
        List of notification dictionaries
    """
    # Return most recent notifications first
    return list(reversed(_notifications))[:limit]
