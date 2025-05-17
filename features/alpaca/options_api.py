"""
Options API Module

This module provides API routes for options data and trading functionality.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from flask import Blueprint, jsonify, request, current_app, Response
from pydantic import BaseModel, validator, Field

from features.alpaca.options import get_options_fetcher
from features.execution.options_trader import get_options_trader, map_side, map_tif

logger = logging.getLogger(__name__)

options_api = Blueprint('options_api', __name__)

# ----------- Pydantic Models for Request Validation -----------

class TargetModel(BaseModel):
    """Target model for options trade exit points."""
    price: float
    percentage: float = Field(ge=0, le=1)
    
    @validator('percentage')
    def validate_percentage(cls, v):
        """Validate percentage is between 0 and 1."""
        if v < 0 or v > 1:
            raise ValueError('Percentage must be between 0 and 1')
        return v


class OptionsTradeRequest(BaseModel):
    """Options trade request model."""
    ticker: str
    direction: str
    targets: List[TargetModel] = []
    
    @validator('direction')
    def validate_direction(cls, v):
        """Validate direction is 'long' or 'short'."""
        if v.lower() not in ('long', 'short'):
            raise ValueError("Direction must be 'long' or 'short'")
        return v.lower()
    
    @validator('targets')
    def validate_targets(cls, v):
        """Validate targets total percentage is approximately 1."""
        if v:
            total = sum(target.percentage for target in v)
            if not (0.98 <= total <= 1.02):  # Allow small rounding errors
                raise ValueError('Target percentages must sum to approximately 1.0')
        return v


# ----------- Helper Functions -----------

def error_response(message: str, status_code: int = 500) -> Response:
    """Create a standardized error response."""
    return jsonify({
        'status': 'error',
        'message': message
    }), status_code


def success_response(data, count: Optional[int] = None) -> Response:
    """Create a standardized success response."""
    response = {
        'status': 'success',
        'data': data
    }
    
    if count is not None:
        response['count'] = count
        
    return jsonify(response)


# ----------- API Routes -----------

@options_api.route('/api/options/chain/<ticker>', methods=['GET'])
def get_options_chain(ticker: str) -> Response:
    """
    Get options chain for a ticker.
    
    Args:
        ticker: Ticker symbol
        
    Query params:
        expiration: Optional expiration date (YYYY-MM-DD)
        strike: Optional strike price
        type: Optional option type ('call' or 'put')
        force_refresh: Whether to force refresh from API (default: false)
    """
    try:
        options_fetcher = get_options_fetcher()
        if not options_fetcher:
            return error_response('Options fetcher not available')
            
        # Parse query parameters
        expiration = request.args.get('expiration')
        strike_price_str = request.args.get('strike')
        option_type = request.args.get('type')
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        # Convert strike price to float if present
        strike_price = None
        if strike_price_str:
            try:
                strike_price = float(strike_price_str)
            except ValueError:
                return error_response('Invalid strike price', 400)
                
        # Get options chain
        options_chain = options_fetcher.get_chain(
            symbol=ticker,
            expiration=expiration,
            strike_price=strike_price,
            option_type=option_type,
            force_refresh=force_refresh
        )
        
        return success_response(options_chain, len(options_chain))
        
    except Exception as e:
        logger.error(f"Error fetching options chain for {ticker}: {e}")
        return error_response(f"Error fetching options chain: {str(e)}")


@options_api.route('/api/options/expirations/<ticker>', methods=['GET'])
def get_options_expirations(ticker: str) -> Response:
    """
    Get available expiration dates for a ticker.
    
    Args:
        ticker: Ticker symbol
    """
    try:
        options_fetcher = get_options_fetcher()
        if not options_fetcher:
            return error_response('Options fetcher not available')
            
        # Get all options to extract expirations
        options_chain = options_fetcher.get_chain(symbol=ticker)
        
        # Extract unique expiration dates
        expirations: Set[str] = set()
        for contract in options_chain:
            if 'expiration' in contract:
                expirations.add(contract['expiration'])
                
        # Sort expirations
        sorted_expirations = sorted(list(expirations))
        
        return success_response(sorted_expirations, len(sorted_expirations))
        
    except Exception as e:
        logger.error(f"Error fetching options expirations for {ticker}: {e}")
        return error_response(f"Error fetching options expirations: {str(e)}")


@options_api.route('/api/options/atm/<ticker>', methods=['GET'])
def get_atm_options(ticker: str) -> Response:
    """
    Get at-the-money options for a ticker.
    
    Args:
        ticker: Ticker symbol
        
    Query params:
        type: Option type ('call' or 'put', default is call)
        delta: Target delta value (default: 0.50)
        expiration: Optional specific expiration date
    """
    try:
        options_fetcher = get_options_fetcher()
        if not options_fetcher:
            return error_response('Options fetcher not available')
            
        # Parse query parameters
        option_type = request.args.get('type', 'call').lower()
        delta_str = request.args.get('delta', '0.50')
        expiration = request.args.get('expiration')
        
        # Convert delta to float
        try:
            target_delta = float(delta_str)
        except ValueError:
            target_delta = 0.50
            
        # Get ATM option
        contract = options_fetcher.find_atm_options(
            symbol=ticker,
            option_type=option_type,
            target_delta=target_delta,
            expiration=expiration
        )
        
        if not contract:
            return error_response(f"No suitable {option_type} option found for {ticker}", 404)
            
        return success_response(contract)
        
    except Exception as e:
        logger.error(f"Error fetching ATM option for {ticker}: {e}")
        return error_response(f"Error fetching ATM option: {str(e)}")


@options_api.route('/api/options/trade', methods=['POST'])
def execute_options_trade() -> Response:
    """
    Execute an options trade based on a signal.
    
    Expected JSON payload:
    {
        "ticker": "SPY",
        "direction": "long",  # or "short"
        "targets": [
            {"price": 455.0, "percentage": 0.50},
            {"price": 460.0, "percentage": 0.50}
        ]
    }
    """
    try:
        options_trader = get_options_trader()
        if not options_trader:
            return error_response('Options trader not available')
            
        # Parse and validate request data using Pydantic
        try:
            json_data = request.json
            if not json_data:
                return error_response('Missing request data', 400)
                
            # Validate with Pydantic model
            trade_request = OptionsTradeRequest(**json_data)
            
        except Exception as validation_error:
            logger.error(f"Invalid trade request format: {validation_error}")
            return error_response(f"Invalid request format: {str(validation_error)}", 400)
            
        # Execute the trade with validated data
        order = options_trader.execute_signal_trade(trade_request.dict())
        
        if not order:
            return error_response('Failed to execute options trade')
            
        return success_response(order)
        
    except Exception as e:
        logger.error(f"Error executing options trade: {e}")
        return error_response(f"Error executing options trade: {str(e)}")


@options_api.route('/api/options/positions', methods=['GET'])
def get_options_positions() -> Response:
    """
    Get current options positions.
    """
    try:
        options_trader = get_options_trader()
        if not options_trader:
            return error_response('Options trader not available')
            
        # This would need to be implemented in the options_trader class
        # For now, just return a placeholder
        return success_response([])
        
    except Exception as e:
        logger.error(f"Error getting options positions: {e}")
        return error_response(f"Error getting options positions: {str(e)}")


@options_api.route('/api/options/positions/<symbol>', methods=['DELETE'])
def close_option_position(symbol: str) -> Response:
    """
    Close an options position.
    
    Args:
        symbol: Options contract symbol to close
        
    Query params:
        percentage: Percentage of position to close (default: 1.0)
    """
    try:
        options_trader = get_options_trader()
        if not options_trader:
            return error_response('Options trader not available')
            
        # Get percentage from query parameters
        percentage_str = request.args.get('percentage', '1.0')
        try:
            percentage = float(percentage_str)
            if percentage <= 0 or percentage > 1:
                return error_response('Percentage must be between 0 and 1', 400)
        except ValueError:
            return error_response('Invalid percentage value', 400)
            
        # Close the position
        result = options_trader.close_position(symbol, percentage)
        
        if not result:
            return error_response(f"Failed to close position for {symbol}")
            
        return success_response(result)
        
    except Exception as e:
        logger.error(f"Error closing options position for {symbol}: {e}")
        return error_response(f"Error closing options position: {str(e)}")


def register_options_api(app):
    """
    Register options API routes with the Flask application.
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(options_api)
    logger.info("Options API routes registered")