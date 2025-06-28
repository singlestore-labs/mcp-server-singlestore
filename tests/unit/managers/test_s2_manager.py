"""Tests for S2Manager class."""

from unittest.mock import patch, MagicMock

from src.api.tools.s2_manager import S2Manager


class TestS2Manager:
    """Tests for S2Manager class."""

    def setup_method(self):
        """Set up common test fixtures before each test method."""
        self.host = "test-host.example.com"
        self.user = "test_user"
        self.password = "test_password"
        self.database = "test_db"

        # Mock connection and cursor
        self.mock_connection = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_connection.cursor.return_value = self.mock_cursor

        # Mock settings
        self.mock_settings = MagicMock()
        self.mock_settings.is_remote = True

    @patch("src.api.tools.s2_manager.version")
    @patch("src.api.tools.s2_manager.get_settings")
    @patch("src.api.tools.s2_manager.s2.connect")
    def test_s2_manager_init_remote_deployment(
        self, mock_connect, mock_get_settings, mock_version
    ):
        """Test S2Manager initialization with remote deployment."""
        # Setup
        mock_get_settings.return_value = self.mock_settings
        mock_version.__version__ = "1.0.0"
        mock_connect.return_value = self.mock_connection

        # Execute
        manager = S2Manager(self.host, self.user, self.password, self.database)

        # Verify
        expected_conn_attrs = {
            "program_name": "Remote MCP Server",
            "program_version": "1.0.0",
        }
        mock_connect.assert_called_once_with(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database,
            conn_attrs=expected_conn_attrs,
        )
        assert manager.host == self.host
        assert manager.user == self.user
        assert manager.password == self.password
        assert manager.database == self.database
        assert manager.connection == self.mock_connection
        assert manager.cursor == self.mock_cursor

    @patch("src.api.tools.s2_manager.version")
    @patch("src.api.tools.s2_manager.get_settings")
    @patch("src.api.tools.s2_manager.s2.connect")
    def test_s2_manager_init_local_deployment(
        self, mock_connect, mock_get_settings, mock_version
    ):
        """Test S2Manager initialization with local deployment."""
        # Setup
        self.mock_settings.is_remote = False
        mock_get_settings.return_value = self.mock_settings
        mock_version.__version__ = "2.1.0"
        mock_connect.return_value = self.mock_connection

        # Execute
        S2Manager(self.host, self.user, self.password)

        # Verify
        expected_conn_attrs = {
            "program_name": "Local MCP Server",
            "program_version": "2.1.0",
        }
        mock_connect.assert_called_once_with(
            host=self.host,
            user=self.user,
            password=self.password,
            database=None,
            conn_attrs=expected_conn_attrs,
        )

    @patch("src.api.tools.s2_manager.version")
    @patch("src.api.tools.s2_manager.get_settings")
    @patch("src.api.tools.s2_manager.s2.connect")
    def test_s2_manager_init_unknown_version(
        self, mock_connect, mock_get_settings, mock_version
    ):
        """Test S2Manager initialization with unknown version."""
        # Setup
        mock_get_settings.return_value = self.mock_settings
        # Simulate missing __version__ attribute
        del mock_version.__version__
        mock_connect.return_value = self.mock_connection

        # Execute
        S2Manager(self.host, self.user, self.password)

        # Verify
        expected_conn_attrs = {
            "program_name": "Remote MCP Server",
            "program_version": "unknown",
        }
        mock_connect.assert_called_once_with(
            host=self.host,
            user=self.user,
            password=self.password,
            database=None,
            conn_attrs=expected_conn_attrs,
        )

    @patch("src.api.tools.s2_manager.version")
    @patch("src.api.tools.s2_manager.get_settings")
    @patch("src.api.tools.s2_manager.s2.connect")
    def test_s2_manager_init_with_extra_kwargs(
        self, mock_connect, mock_get_settings, mock_version
    ):
        """Test S2Manager initialization with extra connection parameters."""
        # Setup
        mock_get_settings.return_value = self.mock_settings
        mock_version.__version__ = "1.0.0"
        mock_connect.return_value = self.mock_connection

        extra_kwargs = {
            "port": 3306,
            "ssl_cert": "/path/to/cert",
            "timeout": 30,
        }

        # Execute
        manager = S2Manager(self.host, self.user, self.password, **extra_kwargs)

        # Verify
        expected_conn_attrs = {
            "program_name": "Remote MCP Server",
            "program_version": "1.0.0",
        }
        mock_connect.assert_called_once_with(
            host=self.host,
            user=self.user,
            password=self.password,
            database=None,
            conn_attrs=expected_conn_attrs,
            port=3306,
            ssl_cert="/path/to/cert",
            timeout=30,
        )
        # Verify that extra_kwargs are preserved (only conn_attrs is popped)
        assert manager.extra_kwargs == extra_kwargs

    @patch("src.api.tools.s2_manager.version")
    @patch("src.api.tools.s2_manager.get_settings")
    @patch("src.api.tools.s2_manager.s2.connect")
    def test_s2_manager_init_with_custom_conn_attrs(
        self, mock_connect, mock_get_settings, mock_version
    ):
        """Test S2Manager initialization with custom connection attributes."""
        # Setup
        mock_get_settings.return_value = self.mock_settings
        mock_version.__version__ = "1.0.0"
        mock_connect.return_value = self.mock_connection

        custom_conn_attrs = {
            "application_name": "Custom App",
            "client_version": "3.0.0",
        }
        extra_kwargs = {
            "conn_attrs": custom_conn_attrs,
            "port": 3306,
        }

        # Execute
        S2Manager(self.host, self.user, self.password, **extra_kwargs)

        # Verify - custom conn_attrs should be merged with default ones
        expected_conn_attrs = {
            "program_name": "Remote MCP Server",
            "program_version": "1.0.0",
            "application_name": "Custom App",
            "client_version": "3.0.0",
        }
        mock_connect.assert_called_once_with(
            host=self.host,
            user=self.user,
            password=self.password,
            database=None,
            conn_attrs=expected_conn_attrs,
            port=3306,
        )

    @patch("src.api.tools.s2_manager.get_settings")
    @patch("src.api.tools.s2_manager.s2.connect")
    def test_execute_query(self, mock_connect, mock_get_settings):
        """Test execute method."""
        # Setup
        mock_get_settings.return_value = self.mock_settings
        mock_connect.return_value = self.mock_connection

        manager = S2Manager(self.host, self.user, self.password)
        query = "SELECT * FROM users WHERE id = %s"
        args = (123,)

        # Execute
        result = manager.execute(query, args)

        # Verify
        self.mock_cursor.execute.assert_called_once_with(query, args=args)
        assert result == self.mock_cursor.execute.return_value

    @patch("src.api.tools.s2_manager.get_settings")
    @patch("src.api.tools.s2_manager.s2.connect")
    def test_execute_query_without_args(self, mock_connect, mock_get_settings):
        """Test execute method without arguments."""
        # Setup
        mock_get_settings.return_value = self.mock_settings
        mock_connect.return_value = self.mock_connection

        manager = S2Manager(self.host, self.user, self.password)
        query = "SELECT COUNT(*) FROM users"

        # Execute
        result = manager.execute(query)

        # Verify
        self.mock_cursor.execute.assert_called_once_with(query, args=None)
        assert result == self.mock_cursor.execute.return_value

    @patch("src.api.tools.s2_manager.get_settings")
    @patch("src.api.tools.s2_manager.s2.connect")
    def test_fetchmany_default_size(self, mock_connect, mock_get_settings):
        """Test fetchmany method with default size."""
        # Setup
        mock_get_settings.return_value = self.mock_settings
        mock_connect.return_value = self.mock_connection

        manager = S2Manager(self.host, self.user, self.password)
        expected_rows = [("user1",), ("user2",), ("user3",)]
        self.mock_cursor.fetchmany.return_value = expected_rows

        # Execute
        result = manager.fetchmany()

        # Verify
        self.mock_cursor.fetchmany.assert_called_once_with(10)
        assert result == expected_rows

    @patch("src.api.tools.s2_manager.get_settings")
    @patch("src.api.tools.s2_manager.s2.connect")
    def test_fetchmany_custom_size(self, mock_connect, mock_get_settings):
        """Test fetchmany method with custom size."""
        # Setup
        mock_get_settings.return_value = self.mock_settings
        mock_connect.return_value = self.mock_connection

        manager = S2Manager(self.host, self.user, self.password)
        expected_rows = [("user1",), ("user2",)]
        self.mock_cursor.fetchmany.return_value = expected_rows

        # Execute
        result = manager.fetchmany(size=2)

        # Verify
        self.mock_cursor.fetchmany.assert_called_once_with(2)
        assert result == expected_rows

    @patch("src.api.tools.s2_manager.get_settings")
    @patch("src.api.tools.s2_manager.s2.connect")
    def test_fetchall(self, mock_connect, mock_get_settings):
        """Test fetchall method."""
        # Setup
        mock_get_settings.return_value = self.mock_settings
        mock_connect.return_value = self.mock_connection

        manager = S2Manager(self.host, self.user, self.password)
        expected_rows = [("user1",), ("user2",), ("user3",), ("user4",)]
        self.mock_cursor.fetchall.return_value = expected_rows

        # Execute
        result = manager.fetchall()

        # Verify
        self.mock_cursor.fetchall.assert_called_once()
        assert result == expected_rows

    @patch("src.api.tools.s2_manager.get_settings")
    @patch("src.api.tools.s2_manager.s2.connect")
    def test_close_connection(self, mock_connect, mock_get_settings):
        """Test close method."""
        # Setup
        mock_get_settings.return_value = self.mock_settings
        mock_connect.return_value = self.mock_connection

        manager = S2Manager(self.host, self.user, self.password)

        # Execute
        manager.close()

        # Verify
        self.mock_cursor.close.assert_called_once()
        self.mock_connection.close.assert_called_once()

    @patch("src.api.tools.s2_manager.get_settings")
    @patch("src.api.tools.s2_manager.s2.connect")
    def test_close_with_none_cursor(self, mock_connect, mock_get_settings):
        """Test close method when cursor is None."""
        # Setup
        mock_get_settings.return_value = self.mock_settings
        mock_connect.return_value = self.mock_connection

        manager = S2Manager(self.host, self.user, self.password)
        manager.cursor = None

        # Execute - should not raise an exception
        manager.close()

        # Verify
        self.mock_connection.close.assert_called_once()

    @patch("src.api.tools.s2_manager.get_settings")
    @patch("src.api.tools.s2_manager.s2.connect")
    def test_close_with_none_connection(self, mock_connect, mock_get_settings):
        """Test close method when connection is None."""
        # Setup
        mock_get_settings.return_value = self.mock_settings
        mock_connect.return_value = self.mock_connection

        manager = S2Manager(self.host, self.user, self.password)
        manager.connection = None

        # Execute - should not raise an exception
        manager.close()

        # Verify
        self.mock_cursor.close.assert_called_once()

    @patch("src.api.tools.s2_manager.get_settings")
    @patch("src.api.tools.s2_manager.s2.connect")
    def test_close_with_both_none(self, mock_connect, mock_get_settings):
        """Test close method when both cursor and connection are None."""
        # Setup
        mock_get_settings.return_value = self.mock_settings
        mock_connect.return_value = self.mock_connection

        manager = S2Manager(self.host, self.user, self.password)
        manager.cursor = None
        manager.connection = None

        # Execute - should not raise an exception
        manager.close()

        # Verify - no close methods should be called
        # This test passes if no exception is raised

    @patch("src.api.tools.s2_manager.version")
    @patch("src.api.tools.s2_manager.get_settings")
    @patch("src.api.tools.s2_manager.s2.connect")
    def test_s2_manager_full_workflow(
        self, mock_connect, mock_get_settings, mock_version
    ):
        """Test a complete S2Manager workflow: init, execute, fetch, close."""
        # Setup
        mock_get_settings.return_value = self.mock_settings
        mock_version.__version__ = "1.0.0"
        mock_connect.return_value = self.mock_connection

        # Mock query results
        self.mock_cursor.fetchall.return_value = [
            (1, "Alice", "alice@example.com"),
            (2, "Bob", "bob@example.com"),
        ]

        # Execute - Initialize manager
        manager = S2Manager(self.host, self.user, self.password, self.database)

        # Execute - Run a query
        query = "SELECT id, name, email FROM users WHERE active = %s"
        manager.execute(query, (True,))

        # Execute - Fetch results
        results = manager.fetchall()

        # Execute - Close connection
        manager.close()

        # Verify - All operations work together
        self.mock_cursor.execute.assert_called_once_with(query, args=(True,))
        self.mock_cursor.fetchall.assert_called_once()
        assert results == [
            (1, "Alice", "alice@example.com"),
            (2, "Bob", "bob@example.com"),
        ]
        self.mock_cursor.close.assert_called_once()
        self.mock_connection.close.assert_called_once()
