import requests

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings

from src.config import app_config


class ServerSettings(BaseSettings):
    """Settings for the simple SingleStore MCP server."""

    # Server settings
    host: str = Field("localhost", env="DEFAULT_HOST")
    port: int = Field(8000, env="DEFAULT_PORT")
    server_url: AnyHttpUrl = Field(
        env="ISSUER_URL",
        default_factory=lambda: AnyHttpUrl(
            f"http://{app_config.settings.server_host}:{app_config.settings.server_port}"
        ),
    )

    singlestore_client_id: str = Field(None, env="SINGLESTORE_CLIENT_ID")
    singlestore_org_id: str = Field(None, env="SINGLESTORE_ORG_ID")
    singlestore_callback_path: AnyHttpUrl = AnyHttpUrl(
        f"http://{app_config.settings.server_host}:{app_config.settings.server_port}/callback"
    )

    # SingleStore OAuth URLs
    singlestore_auth_url: str = ""
    singlestore_token_url: str = ""

    mcp_scope: str = "openid"
    singlestore_scope: str = "openid"

    # Stores temporarily generated code verifier for PKCE. Will be deleted after use.
    singlestore_code_verifier: str = ""

    def __init__(self, **data):
        """Initialize settings with values from environment variables.

        Note: client_id is required but can be
        loaded automatically from environment variables (MCP_SINGLESTORE_SINGLESTORE_CLIENT_ID
        and don't need to be passed explicitly.
        """
        super().__init__(**data)

        self.singlestore_auth_url, self.singlestore_token_url = (
            self.discover_oauth_server()
        )

    def discover_oauth_server(self) -> tuple[str, str]:
        """Discover OAuth server endpoints"""
        discovery_url = (
            f"{app_config.settings.oauth_issuer_url}/.well-known/openid-configuration"
        )
        response = requests.get(discovery_url, timeout=10)
        response.raise_for_status()

        authorization_endpoint: str = response.json().get("authorization_endpoint")

        if not authorization_endpoint:
            raise ValueError("Failed to discover OAuth endpoints")

        token_endpoint: str = response.json().get("token_endpoint")
        if not token_endpoint:
            raise ValueError("Failed to discover OAuth endpoints")

        return authorization_endpoint, token_endpoint
