"""Unit tests for load_credentials function."""

import json
from unittest.mock import patch, mock_open
from tests.models import CredentialsModel


class TestLoadCredentials:
    """Unit tests for the load_credentials function."""

    def test_load_validated_credentials_success(self):
        """Test successfully loading and validating credentials."""
        from src.auth.browser_auth import load_validated_credentials

        # Arrange
        test_credentials = CredentialsModel.create_test_credentials()
        json_content = json.dumps(test_credentials.model_dump())

        with (
            patch("pathlib.Path.exists") as mock_exists,
            patch("builtins.open", mock_open(read_data=json_content)),
        ):
            mock_exists.return_value = True

            # Act
            result = load_validated_credentials()

            # Assert
            assert result is not None
            assert isinstance(result, CredentialsModel)
            assert (
                result.token_set.access_token == test_credentials.token_set.access_token
            )
            assert result.timestamp == test_credentials.timestamp

    def test_load_validated_credentials_invalid_format(self):
        """Test load_validated_credentials with invalid format."""
        from src.auth.browser_auth import load_validated_credentials

        # Arrange - missing required fields
        invalid_data = {"timestamp": 1234567890}
        json_content = json.dumps(invalid_data)

        with (
            patch("pathlib.Path.exists") as mock_exists,
            patch("builtins.open", mock_open(read_data=json_content)),
        ):
            mock_exists.return_value = True

            # Act
            result = load_validated_credentials()

            # Assert
            assert result is None
