"""
Test cases demonstrating UUID validation in the MCP SingleStore server.

This file shows examples of how to properly validate UUID fields using the most
pythonic approaches with Pydantic.
"""

import pytest
from uuid import UUID, uuid4
from pydantic import ValidationError

from src.auth.models.models import (
    AuthorizationParameters,
    TokenRequest,
    RefreshTokenRequest,
    validate_uuid_string,
)
from src.config.config import LocalSettings, RemoteSettings


class TestUUIDValidation:
    """Test cases for UUID validation functionality."""

    def test_validate_uuid_string_valid_uuid(self):
        """Test validate_uuid_string with a valid UUID string."""
        valid_uuid = "b7dbf19e-d140-4334-bae4-e8cd03614485"
        result = validate_uuid_string(valid_uuid)
        assert result == valid_uuid

    def test_validate_uuid_string_uuid_object(self):
        """Test validate_uuid_string with a UUID object."""
        uuid_obj = uuid4()
        result = validate_uuid_string(uuid_obj)
        assert result == str(uuid_obj)

    def test_validate_uuid_string_none(self):
        """Test validate_uuid_string with None."""
        result = validate_uuid_string(None)
        assert result is None

    def test_validate_uuid_string_invalid_format(self):
        """Test validate_uuid_string with invalid UUID format in strict mode."""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            validate_uuid_string("not-a-uuid", strict=True)

    def test_validate_uuid_string_lenient_mode(self):
        """Test validate_uuid_string allows non-UUIDs in lenient mode."""
        result = validate_uuid_string("not-a-uuid", strict=False)
        assert result == "not-a-uuid"

        result = validate_uuid_string("client123", strict=False)
        assert result == "client123"

    def test_validate_uuid_string_wrong_type(self):
        """Test validate_uuid_string with wrong type."""
        with pytest.raises(TypeError, match="Expected UUID string or UUID object"):
            validate_uuid_string(123)

    def test_authorization_parameters_valid_client_id(self):
        """Test AuthorizationParameters with valid client ID UUID."""
        valid_uuid = "b7dbf19e-d140-4334-bae4-e8cd03614485"
        params = AuthorizationParameters(
            client_id=valid_uuid,
            redirect_uri="http://localhost:8080/callback",
            scope="openid profile",
            state="abc123",
            code_challenge="challenge123",
        )
        assert params.client_id == valid_uuid

    def test_authorization_parameters_invalid_client_id(self):
        """Test AuthorizationParameters with invalid client ID in strict mode."""
        import os

        # Temporarily disable test mode to test strict validation
        old_testing = os.environ.get("TESTING")
        old_pytest = os.environ.get("PYTEST_CURRENT_TEST")

        try:
            # Clear test environment variables to enable strict validation
            if "TESTING" in os.environ:
                del os.environ["TESTING"]
            if "PYTEST_CURRENT_TEST" in os.environ:
                del os.environ["PYTEST_CURRENT_TEST"]

            with pytest.raises(ValidationError) as exc_info:
                AuthorizationParameters(
                    client_id="invalid-uuid",
                    redirect_uri="http://localhost:8080/callback",
                    scope="openid profile",
                    state="abc123",
                    code_challenge="challenge123",
                )
            assert "Invalid UUID format" in str(exc_info.value)
        finally:
            # Restore original environment
            if old_testing:
                os.environ["TESTING"] = old_testing
            if old_pytest:
                os.environ["PYTEST_CURRENT_TEST"] = old_pytest

    def test_token_request_valid_client_id(self):
        """Test TokenRequest with valid client ID UUID."""
        valid_uuid = "b7dbf19e-d140-4334-bae4-e8cd03614485"
        request = TokenRequest(
            grant_type="authorization_code",
            code="auth_code_123",
            redirect_uri="http://localhost:8080/callback",
            client_id=valid_uuid,
            code_verifier="verifier123",
        )
        assert request.client_id == valid_uuid

    def test_refresh_token_request_valid_client_id(self):
        """Test RefreshTokenRequest with valid client ID UUID."""
        valid_uuid = "b7dbf19e-d140-4334-bae4-e8cd03614485"
        request = RefreshTokenRequest(
            refresh_token="refresh_token_123", client_id=valid_uuid
        )
        assert request.client_id == valid_uuid

    def test_local_settings_valid_org_id(self):
        """Test LocalSettings with valid org ID UUID."""
        valid_uuid = "b7dbf19e-d140-4334-bae4-e8cd03614485"
        settings = LocalSettings(org_id=valid_uuid)
        assert settings.org_id == valid_uuid

    def test_local_settings_invalid_org_id(self):
        """Test LocalSettings with invalid org ID in strict mode."""
        import os

        # Temporarily disable test mode to test strict validation
        old_testing = os.environ.get("TESTING")
        old_pytest = os.environ.get("PYTEST_CURRENT_TEST")

        try:
            # Clear test environment variables to enable strict validation
            if "TESTING" in os.environ:
                del os.environ["TESTING"]
            if "PYTEST_CURRENT_TEST" in os.environ:
                del os.environ["PYTEST_CURRENT_TEST"]

            with pytest.raises(ValidationError) as exc_info:
                LocalSettings(org_id="invalid-uuid")
            assert "Invalid UUID format" in str(exc_info.value)
        finally:
            # Restore original environment
            if old_testing:
                os.environ["TESTING"] = old_testing
            if old_pytest:
                os.environ["PYTEST_CURRENT_TEST"] = old_pytest

    def test_remote_settings_valid_uuids(self):
        """Test RemoteSettings with valid UUID fields."""
        from unittest.mock import patch
        from src.config.config import Transport

        org_uuid = "b7dbf19e-d140-4334-bae4-e8cd03614485"
        client_uuid = "a6c8e07d-c130-4325-8d2e-d71ba79e2c35"

        # Mock the HTTP request to avoid network calls in tests
        with patch(
            "src.config.config.RemoteSettings.discover_oauth_server"
        ) as mock_discover:
            mock_discover.return_value = (
                "https://auth.example.com/authorize",
                "https://auth.example.com/token",
            )

            settings = RemoteSettings(
                host="localhost",
                org_id=org_uuid,
                transport=Transport.HTTP,
                issuer_url="https://auth.example.com",
                required_scopes=["openid"],
                server_url="http://localhost:8080",
                client_id=client_uuid,
                oauth_db_url="mysql://user:pass@localhost/db",
                segment_write_key="key123",
            )
            assert settings.org_id == org_uuid
            assert settings.client_id == client_uuid


class TestUUIDUsageExamples:
    """Examples of common UUID validation patterns."""

    def test_workspace_id_validation_example(self):
        """Example of how to validate workspace IDs."""

        def validate_workspace_id(workspace_id: str) -> str:
            """Validate that workspace_id is a valid UUID."""
            try:
                UUID(workspace_id)
                return workspace_id
            except ValueError:
                raise ValueError(f"Invalid workspace ID format: {workspace_id}")

        # For demonstration, let's use a pure UUID
        valid_uuid = "12345678-1234-1234-1234-123456789abc"
        result = validate_workspace_id(valid_uuid)
        assert result == valid_uuid

        # Invalid UUID
        with pytest.raises(ValueError):
            validate_workspace_id("not-a-uuid")

    def test_optional_uuid_validation(self):
        """Example of validating optional UUID fields."""
        from typing import Optional

        def validate_optional_uuid(value: Optional[str]) -> Optional[str]:
            """Validate an optional UUID field."""
            if value is None:
                return None
            try:
                UUID(value)
                return value
            except ValueError:
                raise ValueError(f"Invalid UUID format: {value}")

        # Test with None
        assert validate_optional_uuid(None) is None

        # Test with valid UUID
        valid_uuid = "12345678-1234-1234-1234-123456789abc"
        assert validate_optional_uuid(valid_uuid) == valid_uuid

        # Test with invalid UUID
        with pytest.raises(ValueError):
            validate_optional_uuid("invalid")

    def test_uuid_conversion_examples(self):
        """Examples of converting between UUID formats."""

        # String to UUID object
        uuid_str = "b7dbf19e-d140-4334-bae4-e8cd03614485"
        uuid_obj = UUID(uuid_str)
        assert str(uuid_obj) == uuid_str

        # UUID object to string
        new_uuid = uuid4()
        uuid_string = str(new_uuid)
        assert UUID(uuid_string) == new_uuid

        # Validate and normalize UUID format
        def normalize_uuid(value: str) -> str:
            """Normalize UUID to standard format."""
            return str(UUID(value))

        # Test with different case
        mixed_case = "B7DBF19E-d140-4334-bae4-e8cd03614485"
        normalized = normalize_uuid(mixed_case)
        assert normalized == uuid_str.lower()


if __name__ == "__main__":
    pytest.main([__file__])
