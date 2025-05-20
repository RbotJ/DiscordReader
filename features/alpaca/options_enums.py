"""
Options Trading Enums

This module provides enums needed for options trading that may not be available in 
the Alpaca SDK or need to be supplemented.
"""
from enum import Enum, auto

class OptionSide(str, Enum):
    """
    Option contract side (call or put).
    """
    CALL = "call"
    PUT = "put"
    
    def __str__(self):
        return self.value

class OptionType(str, Enum):
    """
    Option contract type.
    """
    STANDARD = "standard"
    
    def __str__(self):
        return self.value
        
class OptionStyle(str, Enum):
    """
    Option contract style (American or European).
    """
    AMERICAN = "american"
    EUROPEAN = "european"
    
    def __str__(self):
        return self.value