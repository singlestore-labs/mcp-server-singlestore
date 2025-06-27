from typing import Union, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime


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
