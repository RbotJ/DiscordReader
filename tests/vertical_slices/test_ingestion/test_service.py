"""
Unit Tests for Ingestion Service

Tests for the store_raw_message function and related storage/deduplication logic.
Covers common scenarios including validation, deduplication, storage, and event emission.
"""
import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from features.ingestion.service import IngestionService
from features.ingestion.store import MessageStore


class TestIngestionService(unittest.TestCase):
    """Test cases for the IngestionService class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = IngestionService()
        self.valid_message = {
            'id': '123456789',
            'channel_id': '987654321',
            'author': 'TestUser',
            'author_id': '555666777',
            'content': 'This is a test message',
            'timestamp': '2025-06-03T12:00:00Z'
        }
        self.invalid_message = {
            'id': '123456789',
            'channel_id': '987654321',
            # Missing required fields: author, content, timestamp
        }
    
    @patch('features.ingestion.service.validate_message')
    @patch('features.ingestion.service.message_store')
    @patch('features.ingestion.service.publish_event')
    def test_store_raw_message_success(self, mock_publish, mock_store, mock_validate):
        """Test successful message storage with all steps."""
        # Arrange
        mock_validate.return_value = True
        mock_store.is_duplicate.return_value = False
        mock_store.insert_message.return_value = True
        
        # Act
        result = self.service.store_raw_message(self.valid_message)
        
        # Assert
        self.assertTrue(result)
        mock_validate.assert_called_once_with(self.valid_message)
        mock_store.is_duplicate.assert_called_once_with('123456789')
        mock_store.insert_message.assert_called_once_with(self.valid_message)
        mock_publish.assert_called_once()
        
        # Verify event payload
        call_args = mock_publish.call_args
        self.assertEqual(call_args[1]['event_type'], 'discord.message.stored')
        self.assertIn('message_id', call_args[1]['payload'])
        self.assertEqual(call_args[1]['payload']['message_id'], '123456789')
    
    @patch('features.ingestion.service.validate_message')
    def test_store_raw_message_validation_failure(self, mock_validate):
        """Test message rejection due to validation failure."""
        # Arrange
        mock_validate.return_value = False
        
        # Act
        result = self.service.store_raw_message(self.invalid_message)
        
        # Assert
        self.assertFalse(result)
        mock_validate.assert_called_once_with(self.invalid_message)
    
    @patch('features.ingestion.service.validate_message')
    @patch('features.ingestion.service.message_store')
    def test_store_raw_message_duplicate_rejection(self, mock_store, mock_validate):
        """Test message rejection due to duplicate detection."""
        # Arrange
        mock_validate.return_value = True
        mock_store.is_duplicate.return_value = True
        
        # Act
        result = self.service.store_raw_message(self.valid_message)
        
        # Assert
        self.assertFalse(result)
        mock_validate.assert_called_once_with(self.valid_message)
        mock_store.is_duplicate.assert_called_once_with('123456789')
        mock_store.insert_message.assert_not_called()
    
    @patch('features.ingestion.service.validate_message')
    @patch('features.ingestion.service.message_store')
    @patch('features.ingestion.service.publish_event')
    def test_store_raw_message_storage_failure(self, mock_publish, mock_store, mock_validate):
        """Test handling of storage failure."""
        # Arrange
        mock_validate.return_value = True
        mock_store.is_duplicate.return_value = False
        mock_store.insert_message.return_value = False
        
        # Act
        result = self.service.store_raw_message(self.valid_message)
        
        # Assert
        self.assertFalse(result)
        mock_validate.assert_called_once_with(self.valid_message)
        mock_store.is_duplicate.assert_called_once_with('123456789')
        mock_store.insert_message.assert_called_once_with(self.valid_message)
        mock_publish.assert_not_called()
    
    @patch('features.ingestion.service.validate_message')
    @patch('features.ingestion.service.message_store')
    @patch('features.ingestion.service.publish_event')
    def test_store_raw_message_event_emission(self, mock_publish, mock_store, mock_validate):
        """Test proper event emission with correct payload structure."""
        # Arrange
        mock_validate.return_value = True
        mock_store.is_duplicate.return_value = False
        mock_store.insert_message.return_value = True
        
        long_content_message = self.valid_message.copy()
        long_content_message['content'] = 'A' * 150  # Long content to test truncation
        
        # Act
        result = self.service.store_raw_message(long_content_message)
        
        # Assert
        self.assertTrue(result)
        mock_publish.assert_called_once()
        
        call_args = mock_publish.call_args
        payload = call_args[1]['payload']
        
        # Verify payload structure
        self.assertIn('message_id', payload)
        self.assertIn('channel_id', payload)
        self.assertIn('content_preview', payload)
        self.assertEqual(payload['message_id'], '123456789')
        self.assertEqual(payload['channel_id'], '987654321')
        
        # Verify content truncation
        self.assertTrue(payload['content_preview'].endswith('...'))
        self.assertLessEqual(len(payload['content_preview']), 103)  # 100 + "..."
    
    @patch('features.ingestion.service.validate_message')
    def test_store_raw_message_exception_handling(self, mock_validate):
        """Test exception handling in store_raw_message."""
        # Arrange
        mock_validate.side_effect = Exception("Validation error")
        
        # Act
        result = self.service.store_raw_message(self.valid_message)
        
        # Assert
        self.assertFalse(result)
    
    def test_store_raw_message_missing_id(self):
        """Test handling of message without ID."""
        # Arrange
        message_without_id = self.valid_message.copy()
        del message_without_id['id']
        
        # Act
        result = self.service.store_raw_message(message_without_id)
        
        # Assert
        self.assertFalse(result)
    
    @patch('features.ingestion.service.validate_message')
    @patch('features.ingestion.service.message_store')
    @patch('features.ingestion.service.publish_event')
    def test_store_raw_message_empty_content(self, mock_publish, mock_store, mock_validate):
        """Test handling of message with empty content."""
        # Arrange
        mock_validate.return_value = True
        mock_store.is_duplicate.return_value = False
        mock_store.insert_message.return_value = True
        
        empty_content_message = self.valid_message.copy()
        empty_content_message['content'] = ''
        
        # Act
        result = self.service.store_raw_message(empty_content_message)
        
        # Assert
        self.assertTrue(result)
        
        # Verify event payload handles empty content
        call_args = mock_publish.call_args
        payload = call_args[1]['payload']
        self.assertEqual(payload['content_preview'], '')


class TestMessageStore(unittest.TestCase):
    """Test cases for the MessageStore class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.store = MessageStore()
        self.valid_message = {
            'id': '123456789',
            'channel_id': '987654321',
            'author': 'TestUser',
            'author_id': '555666777',
            'content': 'This is a test message',
            'timestamp': '2025-06-03T12:00:00Z'
        }
    
    @patch('features.ingestion.store.DiscordMessageModel')
    def test_is_duplicate_true(self, mock_model):
        """Test duplicate detection when message exists."""
        # Arrange
        mock_model.query.filter_by.return_value.first.return_value = Mock()
        
        # Act
        result = self.store.is_duplicate('123456789')
        
        # Assert
        self.assertTrue(result)
        mock_model.query.filter_by.assert_called_once_with(message_id='123456789')
    
    @patch('features.ingestion.store.DiscordMessageModel')
    def test_is_duplicate_false(self, mock_model):
        """Test duplicate detection when message doesn't exist."""
        # Arrange
        mock_model.query.filter_by.return_value.first.return_value = None
        
        # Act
        result = self.store.is_duplicate('123456789')
        
        # Assert
        self.assertFalse(result)
        mock_model.query.filter_by.assert_called_once_with(message_id='123456789')
    
    @patch('features.ingestion.store.DiscordMessageModel')
    @patch('features.ingestion.store.db')
    def test_insert_message_success(self, mock_db, mock_model):
        """Test successful message insertion."""
        # Arrange
        mock_instance = Mock()
        mock_model.from_dict.return_value = mock_instance
        
        # Act
        result = self.store.insert_message(self.valid_message)
        
        # Assert
        self.assertTrue(result)
        mock_model.from_dict.assert_called_once_with(self.valid_message)
        mock_db.session.add.assert_called_once_with(mock_instance)
        mock_db.session.commit.assert_called_once()
    
    @patch('features.ingestion.store.DiscordMessageModel')
    @patch('features.ingestion.store.db')
    def test_insert_message_integrity_error(self, mock_db, mock_model):
        """Test handling of database integrity error (duplicate)."""
        # Arrange
        from sqlalchemy.exc import IntegrityError
        mock_instance = Mock()
        mock_model.from_dict.return_value = mock_instance
        mock_db.session.commit.side_effect = IntegrityError("statement", "params", Exception("Duplicate key"))
        
        # Act
        result = self.store.insert_message(self.valid_message)
        
        # Assert
        self.assertFalse(result)
        mock_db.session.rollback.assert_called_once()
    
    @patch('features.ingestion.store.DiscordMessageModel')
    @patch('features.ingestion.store.db')
    def test_insert_message_general_error(self, mock_db, mock_model):
        """Test handling of general database error."""
        # Arrange
        mock_instance = Mock()
        mock_model.from_dict.return_value = mock_instance
        mock_db.session.commit.side_effect = Exception("Database error")
        
        # Act
        result = self.store.insert_message(self.valid_message)
        
        # Assert
        self.assertFalse(result)
        mock_db.session.rollback.assert_called_once()
    
    @patch('features.ingestion.store.DiscordMessageModel')
    def test_get_message_by_id_found(self, mock_model):
        """Test retrieving an existing message by ID."""
        # Arrange
        mock_message = Mock()
        mock_model.query.filter_by.return_value.first.return_value = mock_message
        
        # Act
        result = self.store.get_message_by_id('123456789')
        
        # Assert
        self.assertEqual(result, mock_message)
        mock_model.query.filter_by.assert_called_once_with(message_id='123456789')
    
    @patch('features.ingestion.store.DiscordMessageModel')
    def test_get_message_by_id_not_found(self, mock_model):
        """Test retrieving a non-existent message by ID."""
        # Arrange
        mock_model.query.filter_by.return_value.first.return_value = None
        
        # Act
        result = self.store.get_message_by_id('123456789')
        
        # Assert
        self.assertIsNone(result)
        mock_model.query.filter_by.assert_called_once_with(message_id='123456789')


if __name__ == '__main__':
    unittest.main()