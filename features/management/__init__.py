"""
Position Management module initialization.
"""
from features.management.position_manager import register_position_routes
from features.management.exit_rules import register_exit_rules_routes

__all__ = ["register_position_routes", "register_exit_rules_routes"]