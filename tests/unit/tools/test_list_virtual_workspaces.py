"""Tests for list_virtual_workspaces tool function."""

from unittest.mock import patch
from uuid import uuid4

from src.api.tools.tools import list_virtual_workspaces


class TestListVirtualWorkspaces:
    """Tests for list_virtual_workspaces function."""

    @patch("src.api.tools.tools.build_request")
    def test_list_virtual_workspaces_success(self, mock_build_request):
        """Test successful virtual workspaces list retrieval."""
        # Setup
        mock_workspaces = [
            {
                "virtualWorkspaceID": f"ws-{uuid4()}",
                "name": "test-workspace-1",
                "endpoint": "https://ws1.example.com",
                "databaseName": "test_db_1",
                "mysqlDmlPort": 3306,
                "webSocketPort": 80,
                "state": "ACTIVE",
            },
            {
                "virtualWorkspaceID": f"ws-{uuid4()}",
                "name": "test-workspace-2",
                "endpoint": "https://ws2.example.com",
                "databaseName": "test_db_2",
                "mysqlDmlPort": 3306,
                "webSocketPort": 80,
                "state": "PAUSED",
            },
            {
                "virtualWorkspaceID": f"ws-{uuid4()}",
                "name": "test-workspace-3",
                "endpoint": "https://ws3.example.com",
                "databaseName": "test_db_3",
                "mysqlDmlPort": 3306,
                "webSocketPort": 80,
                "state": "ACTIVE",
            },
        ]
        mock_build_request.return_value = mock_workspaces

        # Execute
        result = list_virtual_workspaces()

        # Verify
        assert result["status"] == "success"
        assert result["message"] == "Retrieved 3 virtual workspaces"
        assert result["data"]["workspaces"] == mock_workspaces
        assert result["data"]["count"] == 3
        assert result["metadata"]["total_count"] == 3
        assert result["metadata"]["active_count"] == 2  # 2 ACTIVE workspaces

        # Verify API call
        mock_build_request.assert_called_once_with(
            "GET", "sharedtier/virtualWorkspaces"
        )

    @patch("src.api.tools.tools.build_request")
    def test_list_virtual_workspaces_empty(self, mock_build_request):
        """Test virtual workspaces list with empty result."""
        # Setup
        mock_build_request.return_value = []

        # Execute
        result = list_virtual_workspaces()

        # Verify
        assert result["status"] == "success"
        assert result["message"] == "Retrieved 0 virtual workspaces"
        assert len(result["data"]["workspaces"]) == 0
        assert result["data"]["count"] == 0
        assert result["metadata"]["total_count"] == 0
        assert result["metadata"]["active_count"] == 0

    @patch("src.api.tools.tools.build_request")
    def test_list_virtual_workspaces_no_state(self, mock_build_request):
        """Test virtual workspaces list with missing state information."""
        # Setup
        mock_workspaces = [
            {
                "virtualWorkspaceID": f"ws-{uuid4()}",
                "name": "test-workspace",
                "endpoint": "https://ws.example.com",
                "databaseName": "test_db",
                "mysqlDmlPort": 3306,
                "webSocketPort": 80,
                # Missing state field
            }
        ]
        mock_build_request.return_value = mock_workspaces

        # Execute
        result = list_virtual_workspaces()

        # Verify
        assert result["status"] == "success"
        assert result["metadata"]["active_count"] == 0  # No ACTIVE state found
