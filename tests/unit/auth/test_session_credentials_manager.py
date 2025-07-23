"""
Unit tests for SessionCredentialsManager.

This module tests all functionality of the session-based database credentials manager,
including storage, retrieval, invalidation, and key generation.
"""

import unittest
from unittest.mock import patch
import sys
import os

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))

from src.auth.session_credentials_manager import (  # noqa: E402
    SessionCredentialsManager,
    DatabaseCredentials,
    get_session_credentials_manager,
    invalidate_credentials,
    reset_session_credentials_manager,
)


class TestSessionCredentialsManager(unittest.TestCase):
    """Test cases for SessionCredentialsManager class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.manager = SessionCredentialsManager()

    def test_init(self):
        """Test SessionCredentialsManager initialization."""
        manager = SessionCredentialsManager()
        assert manager._credentials == {}

    def test_store_credentials(self):
        """Test storing database credentials."""
        database_key = "workspace1_db1"
        username = "testuser"
        password = "testpass"

        self.manager.store_credentials(database_key, username, password)

        # Verify credentials are stored
        assert database_key in self.manager._credentials
        stored_creds = self.manager._credentials[database_key]
        assert isinstance(stored_creds, DatabaseCredentials)
        assert stored_creds.username == username
        assert stored_creds.password == password

    def test_store_credentials_error_handling(self):
        """Test error handling in store_credentials."""
        with patch(
            "src.auth.session_credentials_manager.DatabaseCredentials",
            side_effect=Exception("Storage error"),
        ):
            with self.assertRaisesRegex(Exception, "Storage error"):
                self.manager.store_credentials("test_key", "user", "pass")

    def test_get_credentials_existing(self):
        """Test retrieving existing credentials."""
        database_key = "workspace1_db1"
        username = "testuser"
        password = "testpass"

        # Store credentials first
        self.manager.store_credentials(database_key, username, password)

        # Retrieve credentials
        result = self.manager.get_credentials(database_key)

        assert result is not None
        assert result == (username, password)

    def test_get_credentials_non_existing(self):
        """Test retrieving non-existing credentials."""
        result = self.manager.get_credentials("non_existing_key")
        assert result is None

    def test_has_credentials_existing(self):
        """Test checking for existing credentials."""
        database_key = "workspace1_db1"
        self.manager.store_credentials(database_key, "user", "pass")

        assert self.manager.has_credentials(database_key) is True

    def test_has_credentials_non_existing(self):
        """Test checking for non-existing credentials."""
        assert self.manager.has_credentials("non_existing_key") is False

    def test_remove_credentials_existing(self):
        """Test removing existing credentials."""
        database_key = "workspace1_db1"
        self.manager.store_credentials(database_key, "user", "pass")

        # Verify credentials exist
        assert self.manager.has_credentials(database_key) is True

        # Remove credentials
        result = self.manager.remove_credentials(database_key)

        # Verify removal
        assert result is True
        assert self.manager.has_credentials(database_key) is False

    def test_remove_credentials_non_existing(self):
        """Test removing non-existing credentials."""
        result = self.manager.remove_credentials("non_existing_key")
        assert result is False

    def test_generate_database_key_with_database_name(self):
        """Test database key generation with database name."""
        workspace_name = "my_workspace"
        database_name = "my_database"

        key = self.manager.generate_database_key(workspace_name, database_name)
        expected_key = f"{workspace_name}_{database_name}"

        assert key == expected_key

    def test_generate_database_key_without_database_name(self):
        """Test database key generation without database name."""
        workspace_name = "my_workspace"

        key = self.manager.generate_database_key(workspace_name)
        expected_key = f"{workspace_name}_None"

        assert key == expected_key

    def test_generate_database_key_with_none_database_name(self):
        """Test database key generation with explicit None database name."""
        workspace_name = "my_workspace"
        database_name = None

        key = self.manager.generate_database_key(workspace_name, database_name)
        expected_key = f"{workspace_name}_None"

        assert key == expected_key

    def test_workflow_integration(self):
        """Test complete workflow integration."""
        workspace_name = "test_workspace"
        database_name = "test_db"
        username = "testuser"
        password = "testpass"

        # Step 1: Generate database key
        key = self.manager.generate_database_key(workspace_name, database_name)
        assert key == "test_workspace_test_db"

        # Step 2: Store credentials
        self.manager.store_credentials(key, username, password)
        assert self.manager.has_credentials(key)

        # Step 3: Retrieve credentials
        retrieved_creds = self.manager.get_credentials(key)
        assert retrieved_creds == (username, password)

        # Step 4: Remove credentials (simulate auth error)
        removed = self.manager.remove_credentials(key)
        assert removed is True
        assert not self.manager.has_credentials(key)

        # Step 5: Verify removal
        retrieved_after_removal = self.manager.get_credentials(key)
        assert retrieved_after_removal is None


class TestDatabaseCredentials(unittest.TestCase):
    """Test cases for DatabaseCredentials dataclass."""

    def test_database_credentials_creation(self):
        """Test DatabaseCredentials creation."""
        username = "testuser"
        password = "testpass"

        creds = DatabaseCredentials(username=username, password=password)

        assert creds.username == username
        assert creds.password == password

    def test_database_credentials_equality(self):
        """Test DatabaseCredentials equality comparison."""
        creds1 = DatabaseCredentials(username="user", password="pass")
        creds2 = DatabaseCredentials(username="user", password="pass")
        creds3 = DatabaseCredentials(username="user", password="different")

        assert creds1 == creds2
        assert creds1 != creds3


class TestGlobalFunctions(unittest.TestCase):
    """Test cases for global utility functions."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Reset global state before each test
        reset_session_credentials_manager()

    def tearDown(self):
        """Clean up after each test method."""
        # Reset global state after each test
        reset_session_credentials_manager()

    def test_get_session_credentials_manager_singleton(self):
        """Test that get_session_credentials_manager returns singleton instance."""
        manager1 = get_session_credentials_manager()
        manager2 = get_session_credentials_manager()

        assert manager1 is manager2
        assert isinstance(manager1, SessionCredentialsManager)

    def test_get_session_credentials_manager_creates_new_instance(self):
        """Test that get_session_credentials_manager creates new instance when none exists."""
        # Ensure no global instance exists
        reset_session_credentials_manager()

        manager = get_session_credentials_manager()

        assert isinstance(manager, SessionCredentialsManager)

    def test_reset_session_credentials_manager(self):
        """Test resetting the global session credentials manager."""
        # Create manager and store some credentials
        manager = get_session_credentials_manager()
        manager.store_credentials("test_key", "user", "pass")
        assert manager.has_credentials("test_key")

        # Reset the manager
        reset_session_credentials_manager()

        # Get new manager (should be different instance)
        new_manager = get_session_credentials_manager()
        assert new_manager is not manager
        assert not new_manager.has_credentials("test_key")

    def test_invalidate_credentials(self):
        """Test the invalidate_credentials utility function."""
        # Get manager and store credentials
        manager = get_session_credentials_manager()
        database_key = "test_workspace_test_db"
        manager.store_credentials(database_key, "user", "pass")

        # Verify credentials exist
        assert manager.has_credentials(database_key)

        # Invalidate credentials
        invalidate_credentials(database_key)

        # Verify credentials are removed
        assert not manager.has_credentials(database_key)

    def test_invalidate_credentials_non_existing(self):
        """Test invalidating non-existing credentials."""
        # This should not raise an exception
        invalidate_credentials("non_existing_key")

        # Verify manager still works
        manager = get_session_credentials_manager()
        assert isinstance(manager, SessionCredentialsManager)


class TestErrorScenarios(unittest.TestCase):
    """Test cases for error scenarios and edge cases."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.manager = SessionCredentialsManager()

    def test_empty_database_key(self):
        """Test handling of empty database key."""
        # Store with empty key
        self.manager.store_credentials("", "user", "pass")
        assert self.manager.has_credentials("")

        # Retrieve with empty key
        result = self.manager.get_credentials("")
        assert result == ("user", "pass")

    def test_empty_credentials(self):
        """Test handling of empty username/password."""
        database_key = "test_key"

        # Store empty credentials
        self.manager.store_credentials(database_key, "", "")

        # Verify they are stored and retrievable
        result = self.manager.get_credentials(database_key)
        assert result == ("", "")

    def test_special_characters_in_keys(self):
        """Test handling of special characters in database keys."""
        special_keys = [
            "workspace@domain_db#test",
            "workspace with spaces_db",
            "workspace_db$pecial",
            "workspace_db-with-dashes",
            "workspace_db.with.dots",
        ]

        for key in special_keys:
            self.manager.store_credentials(key, f"user_{key}", f"pass_{key}")
            assert self.manager.has_credentials(key)

            result = self.manager.get_credentials(key)
            assert result == (f"user_{key}", f"pass_{key}")

    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        database_key = "workspace_测试数据库"
        username = "用户名"
        password = "密码"

        self.manager.store_credentials(database_key, username, password)
        result = self.manager.get_credentials(database_key)

        assert result == (username, password)

    def test_very_long_keys_and_values(self):
        """Test handling of very long keys and values."""
        long_key = "workspace_" + "a" * 1000
        long_username = "user_" + "b" * 1000
        long_password = "pass_" + "c" * 1000

        self.manager.store_credentials(long_key, long_username, long_password)
        result = self.manager.get_credentials(long_key)

        assert result == (long_username, long_password)


class TestPerformance(unittest.TestCase):
    """Test cases for performance characteristics."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.manager = SessionCredentialsManager()

    def test_large_number_of_credentials(self):
        """Test handling a large number of credentials."""
        num_credentials = 1000

        # Store many credentials
        for i in range(num_credentials):
            key = f"workspace_{i}_db_{i}"
            username = f"user_{i}"
            password = f"pass_{i}"
            self.manager.store_credentials(key, username, password)

        # Verify all are stored
        assert len(self.manager._credentials) == num_credentials

        # Test retrieval performance
        for i in range(0, num_credentials, 100):  # Sample every 100th
            key = f"workspace_{i}_db_{i}"
            result = self.manager.get_credentials(key)
            assert result == (f"user_{i}", f"pass_{i}")


if __name__ == "__main__":
    # Run tests if executed directly
    unittest.main(verbosity=2)
