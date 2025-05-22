"""
Discord Tests Module

This module provides test utilities for Discord integration.
"""
from features.discord.tests.simple_test import (
    run_simple_test,
    test_discord_connection,
    fetch_test_message,
    send_test_message
)

__all__ = [
    'run_simple_test',
    'test_discord_connection',
    'fetch_test_message',
    'send_test_message'
]