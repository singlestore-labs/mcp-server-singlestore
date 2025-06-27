"""Unit tests for save_credentials function."""

import json
from unittest.mock import patch, mock_open, MagicMock

from src.auth.browser_auth import save_credentials
from tests.models import TokenSetModel
from tests.models import CredentialsModel


class TestSaveCredentials:
    """Unit tests for the save_credentials function."""

    def test_save_credentials_success(self):
        """Test successfully saving credentials."""
        # Arrange
        test_token_data = {
            "access_token": "test_access_token",
            "token_type": "Bearer",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
            "id_token": "test_id_token",
            "state": "test_state",
            "expires_at": 1734567890123,
        }
        token_set = TokenSetModel.model_validate(test_token_data)

        # Create a more sophisticated mock that captures written content
        written_content = []

        def mock_write(content):
            written_content.append(content)

        mock_file_handle = MagicMock()
        mock_file_handle.write = mock_write
        mock_file = mock_open()
        mock_file.return_value.__enter__.return_value = mock_file_handle

        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("builtins.open", mock_file),
            patch("os.chmod") as mock_chmod,
            patch("time.time", return_value=1234567890.0),
        ):
            # Act
            save_credentials(token_set)

            # Assert
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
            mock_file.assert_called_once()
            mock_chmod.assert_called_once()

            # Verify the JSON content written
            assert len(written_content) > 0
            full_content = "".join(written_content)
            saved_data = json.loads(full_content)

            # Validate structure using Pydantic
            credentials = CredentialsModel.model_validate(saved_data)
            assert credentials.token_set.access_token == test_token_data["access_token"]
            assert credentials.token_set.token_type == test_token_data["token_type"]
            assert credentials.timestamp == 1234567890.0

    def test_save_credentials_creates_directory(self):
        """Test that save_credentials creates the parent directory if it doesn't exist."""
        # Arrange
        test_token_data = {"access_token": "test", "token_type": "Bearer"}
        token_set = TokenSetModel.model_validate(test_token_data)

        mock_file = mock_open()
        mock_home = MagicMock()
        mock_credentials_path = MagicMock()
        mock_home.__truediv__.return_value.__truediv__.return_value = (
            mock_credentials_path
        )

        with (
            patch("pathlib.Path.home", return_value=mock_home),
            patch("builtins.open", mock_file),
            patch("os.chmod"),
            patch("time.time", return_value=1234567890.0),
        ):
            # Act
            save_credentials(token_set)

            # Assert
            mock_credentials_path.parent.mkdir.assert_called_once_with(
                parents=True, exist_ok=True
            )

    def test_save_credentials_sets_secure_permissions(self):
        """Test that save_credentials sets secure file permissions (0o600)."""
        # Arrange
        test_token_data = {"access_token": "test", "token_type": "Bearer"}
        token_set = TokenSetModel.model_validate(test_token_data)

        mock_file = mock_open()
        mock_home = MagicMock()
        mock_credentials_path = MagicMock()
        mock_home.__truediv__.return_value.__truediv__.return_value = (
            mock_credentials_path
        )

        with (
            patch("pathlib.Path.home", return_value=mock_home),
            patch("builtins.open", mock_file),
            patch("os.chmod") as mock_chmod,
            patch("time.time", return_value=1234567890.0),
        ):
            # Act
            save_credentials(token_set)

            # Assert
            mock_chmod.assert_called_once_with(mock_credentials_path, 0o600)

    def test_save_credentials_includes_timestamp(self):
        """Test that save_credentials includes a timestamp."""
        # Arrange
        test_token_data = {"access_token": "test", "token_type": "Bearer"}
        token_set = TokenSetModel.model_validate(test_token_data)

        written_content = []

        def mock_write(content):
            written_content.append(content)

        mock_file_handle = MagicMock()
        mock_file_handle.write = mock_write
        mock_file = mock_open()
        mock_file.return_value.__enter__.return_value = mock_file_handle

        expected_timestamp = 1234567890.5

        with (
            patch("pathlib.Path.mkdir"),
            patch("builtins.open", mock_file),
            patch("os.chmod"),
            patch("time.time", return_value=expected_timestamp),
        ):
            # Act
            save_credentials(token_set)

            # Assert
            assert len(written_content) > 0
            full_content = "".join(written_content)
            saved_data = json.loads(full_content)

            assert "timestamp" in saved_data
            assert saved_data["timestamp"] == expected_timestamp

    def test_save_credentials_preserves_token_data(self):
        """Test that save_credentials preserves all token data correctly."""
        # Arrange
        test_credentials = CredentialsModel.create_test_credentials()
        token_set = TokenSetModel.model_validate(
            test_credentials.token_set.model_dump()
        )

        written_content = []

        def mock_write(content):
            written_content.append(content)

        mock_file_handle = MagicMock()
        mock_file_handle.write = mock_write
        mock_file = mock_open()
        mock_file.return_value.__enter__.return_value = mock_file_handle

        with (
            patch("pathlib.Path.mkdir"),
            patch("builtins.open", mock_file),
            patch("os.chmod"),
            patch("time.time", return_value=test_credentials.timestamp),
        ):
            # Act
            save_credentials(token_set)

            # Assert
            assert len(written_content) > 0
            full_content = "".join(written_content)
            saved_data = json.loads(full_content)

            # Validate using Pydantic
            credentials = CredentialsModel.model_validate(saved_data)

            # Check all token fields are preserved
            assert (
                credentials.token_set.access_token
                == test_credentials.token_set.access_token
            )
            assert (
                credentials.token_set.token_type
                == test_credentials.token_set.token_type
            )
            assert (
                credentials.token_set.refresh_token
                == test_credentials.token_set.refresh_token
            )
            assert (
                credentials.token_set.expires_in
                == test_credentials.token_set.expires_in
            )
            assert credentials.token_set.id_token == test_credentials.token_set.id_token
            assert credentials.token_set.state == test_credentials.token_set.state
            assert (
                credentials.token_set.expires_at
                == test_credentials.token_set.expires_at
            )

    def test_save_credentials_json_formatting(self):
        """Test that save_credentials formats JSON with proper indentation."""
        # Arrange
        test_token_data = {"access_token": "test", "token_type": "Bearer"}
        token_set = TokenSetModel.model_validate(test_token_data)

        written_content = []

        def mock_write(content):
            written_content.append(content)

        mock_file_handle = MagicMock()
        mock_file_handle.write = mock_write
        mock_file = mock_open()
        mock_file.return_value.__enter__.return_value = mock_file_handle

        with (
            patch("pathlib.Path.mkdir"),
            patch("builtins.open", mock_file),
            patch("os.chmod"),
            patch("time.time", return_value=1234567890.0),
        ):
            # Act
            save_credentials(token_set)

            # Assert
            assert len(written_content) > 0
            full_content = "".join(written_content)

            # Verify the JSON is properly formatted (contains newlines for indentation)
            assert "\n" in full_content
            assert "  " in full_content  # Should have indentation spaces

            # Verify it's valid JSON
            parsed_data = json.loads(full_content)
            assert "token_set" in parsed_data
            assert "timestamp" in parsed_data

    def test_save_credentials_with_extra_token_fields(self):
        """Test that save_credentials preserves extra fields in token data."""
        # Arrange
        test_token_data = {
            "access_token": "test",
            "token_type": "Bearer",
            "extra_field": "extra_value",
            "custom_data": {"nested": "value"},
        }
        token_set = TokenSetModel.model_validate(test_token_data)

        written_content = []

        def mock_write(content):
            written_content.append(content)

        mock_file_handle = MagicMock()
        mock_file_handle.write = mock_write
        mock_file = mock_open()
        mock_file.return_value.__enter__.return_value = mock_file_handle

        with (
            patch("pathlib.Path.mkdir"),
            patch("builtins.open", mock_file),
            patch("os.chmod"),
            patch("time.time", return_value=1234567890.0),
        ):
            # Act
            save_credentials(token_set)

            # Assert
            assert len(written_content) > 0
            full_content = "".join(written_content)
            saved_data = json.loads(full_content)

            # Verify extra fields are preserved
            assert saved_data["token_set"]["extra_field"] == "extra_value"
            assert saved_data["token_set"]["custom_data"] == {"nested": "value"}
