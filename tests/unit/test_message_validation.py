
import unittest
from features.discord.message_fetcher import validate_message

class TestMessageValidation(unittest.TestCase):
    def test_valid_message(self):
        message = {
            'id': '123456789',
            'content': 'Test message',
            'author': 'TestUser#1234',
            'timestamp': '2025-05-16T12:00:00+00:00'
        }
        self.assertTrue(validate_message(message))
    
    def test_missing_required_fields(self):
        invalid_messages = [
            {'content': 'Missing ID'},
            {'id': '123', 'content': 'Missing author'},
            {'id': '123', 'author': 'Test', 'content': 'Missing timestamp'},
        ]
        for msg in invalid_messages:
            self.assertFalse(validate_message(msg))
    
    def test_empty_fields(self):
        message = {
            'id': '',
            'content': '',
            'author': '',
            'timestamp': ''
        }
        self.assertFalse(validate_message(message))

if __name__ == '__main__':
    unittest.main()
