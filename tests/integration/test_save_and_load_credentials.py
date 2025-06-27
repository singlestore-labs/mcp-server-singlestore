"""Integration tests for save and load credentials functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from src.auth.browser_auth import save_credentials, load_validated_credentials
from tests.models import TokenSetModel, CredentialsModel


class TestSaveAndLoadCredentialsIntegration:
    """Integration tests for save and load credentials together."""

    def test_save_and_load_credentials_roundtrip(self):
        """Test saving and loading credentials works correctly together."""
        # Arrange
        test_credentials = CredentialsModel.create_test_credentials()
        token_set = TokenSetModel.model_validate(
            test_credentials.token_set.model_dump()
        )

        # Use a temporary file for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = Path(temp_dir) / "test_credentials.json"

            with patch("src.auth.browser_auth.CREDENTIALS_FILE", temp_file):
                # Act - Save credentials
                save_credentials(token_set)

                # Act - Load credentials
                result = load_validated_credentials()

                # Assert
                assert result is not None

                # Validate using Pydantic model
                loaded_credentials = CredentialsModel.model_validate(result)

                # Verify all token data matches
                assert (
                    loaded_credentials.token_set.access_token
                    == test_credentials.token_set.access_token
                )
                assert (
                    loaded_credentials.token_set.token_type
                    == test_credentials.token_set.token_type
                )
                assert (
                    loaded_credentials.token_set.refresh_token
                    == test_credentials.token_set.refresh_token
                )
                assert (
                    loaded_credentials.token_set.expires_in
                    == test_credentials.token_set.expires_in
                )
                assert (
                    loaded_credentials.token_set.id_token
                    == test_credentials.token_set.id_token
                )
                assert (
                    loaded_credentials.token_set.state
                    == test_credentials.token_set.state
                )
                assert (
                    loaded_credentials.token_set.expires_at
                    == test_credentials.token_set.expires_at
                )

                # Timestamp should be present and numeric
                assert isinstance(loaded_credentials.timestamp, (int, float))
