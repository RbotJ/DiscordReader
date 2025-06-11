"""
Unit Test for Discord Message Fetcher

Tests the functionality of the message fetcher, specifically checking
that forwarded messages are properly detected and processed.
"""
import unittest
import asyncio
import json
import os
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from common.utils import utc_now

# Path to the module to test
import sys
sys.path.append(os.path.abspath('.'))
from features.discord.message_fetcher import fetch_latest_messages, store_raw_messages


class MessageFetcherTest(unittest.TestCase):
    """Tests for the Discord message fetcher functionality."""
    
    def test_store_raw_messages(self):
        """Test that messages are properly stored to a file."""
        messages = [
            {
                'id': '123456789',
                'author': 'TestUser#1234',
                'content': 'Test message',
                'timestamp': utc_now().isoformat(),
                'is_forwarded': False
            }
        ]
        
        test_filename = 'test_messages.json'
        result = store_raw_messages(messages, test_filename)
        self.assertTrue(result)
        
        # Check that the file exists and has the correct content
        self.assertTrue(os.path.exists(test_filename))
        
        with open(test_filename, 'r') as f:
            stored_messages = json.load(f)
        
        self.assertEqual(len(stored_messages), 1)
        self.assertEqual(stored_messages[0]['id'], '123456789')
        
        # Clean up the test file
        os.remove(test_filename)
    
    @patch('features.discord.message_fetcher.discord.Client')
    def test_fetch_messages_with_forwarded(self, mock_client_class):
        """Test that forwarded messages are properly processed."""
        # Set up mock message objects
        mock_channel = MagicMock()
        
        # Original message that will be referenced
        original_message = MagicMock()
        original_message.id = '111111111'
        original_message.author.name = 'OriginalUser#1234'
        original_message.author.id = '22222'
        original_message.content = 'Original message content'
        original_message.created_at.isoformat.return_value = '2025-05-16T12:00:00+00:00'
        original_message.attachments = []
        original_message.embeds = []
        
        # Message that references the original message (a forwarded message)
        forwarded_message = MagicMock()
        forwarded_message.id = '333333333'
        forwarded_message.author.name = 'ForwardingUser#5678'
        forwarded_message.author.id = '44444'
        forwarded_message.content = 'Check out this message!'
        forwarded_message.created_at.isoformat.return_value = '2025-05-17T12:00:00+00:00'
        forwarded_message.attachments = []
        forwarded_message.embeds = []
        
        # Set up the reference
        forwarded_message.reference = MagicMock()
        forwarded_message.reference.resolved = None  # Force it to fetch the message
        forwarded_message.reference.message_id = '111111111'
        
        # Regular message with no reference
        regular_message = MagicMock()
        regular_message.id = '555555555'
        regular_message.author.name = 'RegularUser#9012'
        regular_message.author.id = '66666'
        regular_message.content = 'Just a regular message'
        regular_message.created_at.isoformat.return_value = '2025-05-17T13:00:00+00:00'
        regular_message.attachments = []
        regular_message.embeds = []
        regular_message.reference = None
        
        # Set up the mock channel to return our test messages
        mock_channel.history.return_value.__aiter__.return_value = [
            forwarded_message,
            regular_message
        ]
        
        # Make channel.fetch_message return our original message
        async def mock_fetch_message(message_id):
            if message_id == '111111111':
                return original_message
            return None
        
        mock_channel.fetch_message = mock_fetch_message
        
        # Set up the mock client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Set up the on_ready event handler
        on_ready_callback = None
        
        async def mock_start(token):
            # Call the on_ready event handler
            if on_ready_callback:
                await on_ready_callback()
        
        mock_client.start = mock_start
        
        # Capture the on_ready event handler when it's registered
        def mock_event(event_name):
            def decorator(func):
                nonlocal on_ready_callback
                if event_name == 'on_ready':
                    on_ready_callback = func
                return func
            return decorator
        
        mock_client.event = mock_event
        
        # Make get_channel return our mock channel
        mock_client.get_channel.return_value = mock_channel
        
        # Run the test
        async def run_test():
            messages = await fetch_latest_messages(123456, limit=10)
            
            # Check that we got 2 messages
            self.assertEqual(len(messages), 2)
            
            # Check that the forwarded message is marked correctly
            forwarded_msg = messages[0]  # First message should be the forwarded one
            self.assertTrue(forwarded_msg['is_forwarded'])
            self.assertIn('forwarded', forwarded_msg)
            
            # Check that the forwarded content is correct
            self.assertEqual(forwarded_msg['forwarded']['id'], '111111111')
            self.assertEqual(forwarded_msg['forwarded']['content'], 'Original message content')
            
            # Check that the regular message is not marked as forwarded
            regular_msg = messages[1]
            self.assertFalse(regular_msg['is_forwarded'])
            self.assertNotIn('forwarded', regular_msg)
        
        # Run the test in an event loop
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(run_test())
        finally:
            loop.close()


if __name__ == '__main__':
    unittest.main()