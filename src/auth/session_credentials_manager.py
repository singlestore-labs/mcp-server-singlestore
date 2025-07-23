"""
Session-based database credentials manager for local server use.

This module provides a simple in-memory credential storage system for managing
database credentials during a single user session.
"""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from src.logger import get_logger

logger = get_logger()


@dataclass
class DatabaseCredentials:
    """Simple database credentials container."""

    username: str
    password: str


class SessionCredentialsManager:
    """
    Simple session-based database credentials manager for local server use.

    This class provides basic in-memory storage for database credentials
    during a single user session.
    """

    def __init__(self):
        """Initialize the credentials manager."""
        self._credentials: Dict[str, DatabaseCredentials] = {}
        logger.debug("SessionCredentialsManager initialized")

    def store_credentials(
        self, database_name: str, username: str, password: str
    ) -> None:
        """
        Store database credentials.

        Args:
            database_name: Name of the database
            username: Database username
            password: Database password
        """
        try:
            credentials = DatabaseCredentials(username=username, password=password)
            self._credentials[database_name] = credentials
            logger.debug(f"Stored credentials for database: {database_name}")
        except Exception as e:
            logger.error(
                f"Failed to store credentials for database {database_name}: {e}"
            )
            raise

    def get_credentials(self, database_name: str) -> Optional[Tuple[str, str]]:
        """
        Retrieve database credentials.

        Args:
            database_name: Name of the database

        Returns:
            Tuple of (username, password) if credentials exist, None otherwise
        """
        credentials = self._credentials.get(database_name)
        if credentials:
            logger.debug(f"Retrieved credentials for database: {database_name}")
            return credentials.username, credentials.password
        logger.debug(f"No credentials found for database: {database_name}")
        return None

    def has_credentials(self, database_name: str) -> bool:
        """
        Check if credentials exist for a database.

        Args:
            database_name: Name of the database

        Returns:
            True if credentials exist, False otherwise
        """
        return database_name in self._credentials

    def remove_credentials(self, database_name: str) -> bool:
        """
        Remove credentials for a specific database.

        This should be called when authentication fails to clear invalid credentials.

        Args:
            database_name: Name of the database

        Returns:
            True if credentials were removed, False if they didn't exist
        """
        if database_name in self._credentials:
            del self._credentials[database_name]
            logger.info(f"Removed invalid credentials for database: {database_name}")
            return True
        logger.debug(f"No credentials to remove for database: {database_name}")
        return False

    def generate_database_key(
        self, workspace_name: str, database_name: str = None
    ) -> str:
        """
        Generate a unique database key for credential storage.

        This method creates a consistent key format for storing and retrieving
        credentials based on workspace name and database name.

        Args:
            workspace_name: Name of the workspace
            database_name: Optional database name

        Returns:
            Unique database key in format: "{workspace_name}_{database_name}"
        """
        key = f"{workspace_name}_{database_name}"
        logger.debug(f"Generated database key: {key}")
        return key


# Global session credentials manager instance
_session_credentials_manager: Optional[SessionCredentialsManager] = None


def get_session_credentials_manager() -> SessionCredentialsManager:
    """
    Get or create the global session credentials manager.

    Returns:
        SessionCredentialsManager instance
    """
    global _session_credentials_manager

    if _session_credentials_manager is None:
        _session_credentials_manager = SessionCredentialsManager()
        logger.info("Created new session credentials manager")

    return _session_credentials_manager


def reset_session_credentials_manager() -> None:
    """
    Reset the global session credentials manager.

    This creates a new instance, effectively clearing all stored credentials.
    """
    global _session_credentials_manager
    _session_credentials_manager = None
    logger.info("Reset session credentials manager")


def invalidate_credentials(database_name: str) -> None:
    """
    Invalidate credentials for a specific database.

    This should be called when authentication fails to clear invalid credentials.

    Args:
        database_name: Name of the database with invalid credentials
    """
    manager = get_session_credentials_manager()
    manager.remove_credentials(database_name)
