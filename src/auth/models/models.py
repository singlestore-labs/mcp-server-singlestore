from typing import Union, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime

from src.utils.uuid_validation import validate_uuid_string


# Pydantic models for OAuth server responses
class OAuthServerConfig(BaseModel):
    """Model for OAuth server configuration endpoints."""

    authorization_endpoint: str = Field(..., description="Authorization endpoint URL")
    token_endpoint: str = Field(..., description="Token endpoint URL")

    model_config = ConfigDict(extra="allow")


class PKCEData(BaseModel):
    """Model for PKCE code verifier and challenge data."""

    code_verifier: str = Field(..., description="PKCE code verifier")
    code_challenge: str = Field(..., description="PKCE code challenge")
    state: str = Field(..., description="OAuth state parameter")


class AuthorizationParameters(BaseModel):
    """Model for OAuth authorization parameters."""

    client_id: str = Field(..., description="OAuth client ID")
    redirect_uri: str = Field(..., description="Redirect URI")
    response_type: str = Field(default="code", description="OAuth response type")
    scope: str = Field(..., description="OAuth scopes")
    state: str = Field(..., description="OAuth state parameter")
    code_challenge: str = Field(..., description="PKCE code challenge")
    code_challenge_method: str = Field(
        default="S256", description="PKCE code challenge method"
    )

    @field_validator("client_id", mode="before")
    @classmethod
    def validate_client_id_uuid(cls, v):
        """Validate that client_id is a valid UUID."""
        return validate_uuid_string(v)


class CallbackParameters(BaseModel):
    """Model for OAuth callback parameters."""

    code: Optional[str] = Field(None, description="Authorization code")
    state: Optional[str] = Field(None, description="OAuth state parameter")
    error: Optional[str] = Field(None, description="Error code")
    error_description: Optional[str] = Field(None, description="Error description")


class TokenRequest(BaseModel):
    """Model for OAuth token request data."""

    grant_type: str = Field(..., description="OAuth grant type")
    code: str = Field(..., description="Authorization code")
    redirect_uri: str = Field(..., description="Redirect URI")
    client_id: str = Field(..., description="OAuth client ID")
    code_verifier: str = Field(..., description="PKCE code verifier")

    @field_validator("client_id", mode="before")
    @classmethod
    def validate_client_id_uuid(cls, v):
        """Validate that client_id is a valid UUID."""
        return validate_uuid_string(v)


class TokenResponse(BaseModel):
    """Model for OAuth token response."""

    access_token: Optional[str] = Field(None, description="Access token")
    token_type: Optional[str] = Field(None, description="Token type")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    expires_in: Optional[int] = Field(None, description="Token expiration in seconds")
    id_token: Optional[str] = Field(None, description="ID token")
    scope: Optional[str] = Field(None, description="Granted scopes")
    error: Optional[str] = Field(None, description="Error code")
    error_description: Optional[str] = Field(None, description="Error description")

    model_config = ConfigDict(extra="allow")


# Pydantic models for credentials
class TokenSetModel(BaseModel):
    """Model for OAuth token set."""

    model_config = ConfigDict(extra="allow")

    access_token: str = Field(..., description="The access token")
    token_type: str = Field(..., description="Token type (typically 'Bearer')")
    refresh_token: Optional[str] = Field(None, description="The refresh token")
    expires_in: Optional[int] = Field(
        None, description="Token expiration time in seconds"
    )
    id_token: Optional[str] = Field(None, description="The ID token")
    state: Optional[str] = Field(None, description="OAuth state parameter")
    expires_at: Optional[Union[int, float]] = Field(
        None, description="Absolute expiration timestamp"
    )

    @field_validator("expires_at", mode="before")
    @classmethod
    def convert_expires_at_to_int(cls, v):
        """Convert float timestamps to integers for backward compatibility."""
        if v is None:
            return v
        if isinstance(v, (int, float)):
            return int(v)
        return v

    def is_expired(self) -> bool:
        """Check if the token is expired."""
        if self.expires_at is None:
            return False
        return datetime.now().timestamp() >= self.expires_at


class CredentialsModel(BaseModel):
    """Model for authentication credentials."""

    token_set: TokenSetModel = Field(..., description="OAuth token set")
    timestamp: Union[int, float] = Field(
        ..., description="Timestamp when credentials were saved"
    )

    @classmethod
    def create_test_credentials(cls) -> "CredentialsModel":
        """Create valid test credentials for testing purposes."""
        return cls(
            token_set=TokenSetModel(
                access_token="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
                token_type="Bearer",
                refresh_token="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9_refresh...",
                expires_in=3600,
                id_token="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9_id...",
                state="abc123def456",
                expires_at=1734567890123,
            ),
            timestamp=1734567890000,
        )


class RefreshTokenRequest(BaseModel):
    """Model for OAuth refresh token request data."""

    grant_type: str = Field(default="refresh_token", description="OAuth grant type")
    refresh_token: str = Field(..., description="Refresh token")
    client_id: str = Field(..., description="OAuth client ID")

    @field_validator("client_id", mode="before")
    @classmethod
    def validate_client_id_uuid(cls, v):
        """Validate that client_id is a valid UUID."""
        return validate_uuid_string(v)


class TokenValidationResult(BaseModel):
    """Model for token validation result."""

    is_valid: bool = Field(..., description="Whether the token is valid")
    is_expired: bool = Field(..., description="Whether the token is expired")
    needs_refresh: bool = Field(..., description="Whether the token needs refresh")
    has_refresh_token: bool = Field(
        ..., description="Whether refresh token is available"
    )
