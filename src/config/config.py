from typing import List, cast
from urllib.parse import urljoin
import requests

from abc import ABC
from contextvars import ContextVar
from enum import Enum
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.requests import Request
from src.analytics.manager import AnalyticsManager


class Transport(str, Enum):
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "streamable-http"


class AuthMethod(str, Enum):
    API_KEY = "api_key"
    OAUTH_TOKEN = "oauth_token"


class Settings(ABC, BaseSettings):
    host: str = "localhost"
    port: int = 8000
    s2_api_base_url: str = "https://api.singlestore.com"
    graphql_public_endpoint: str = "https://backend.singlestore.com/public"
    transport: Transport
    is_remote: bool


class LocalSettings(Settings):
    api_key: str | None = None
    org_id: str | None = (
        None  # Added to support organization selection for OAuth token auth
    )
    auth_method: AuthMethod = AuthMethod.API_KEY
    transport: Transport = Transport.STDIO
    is_remote: bool = False

    model_config = SettingsConfigDict(env_prefix="MCP_", env_file=".env.local")

    def set_oauth_token(self, token: str) -> None:
        """Set OAuth token as the authentication method"""
        self.api_key = token
        self.auth_method = AuthMethod.OAUTH_TOKEN

    analytics_manager: AnalyticsManager = AnalyticsManager(enabled=False)


class RemoteSettings(Settings):
    host: str
    org_id: str
    is_remote: bool = True
    issuer_url: str
    required_scopes: List[str]
    server_url: AnyHttpUrl
    client_id: str
    callback_path: AnyHttpUrl | None = None
    # SingleStore OAuth URLs
    singlestore_auth_url: str | None = None
    singlestore_token_url: str | None = None
    # SingleStore DB URL for OAuth provider storage
    oauth_db_url: str
    # Stores temporarily generated code verifier for PKCE. Will be deleted after use.
    singlestore_code_verifier: str = ""
    # Segment analytics write key
    segment_write_key: str
    # Analytics manager instance
    analytics_manager: AnalyticsManager | None = None

    model_config = SettingsConfigDict(env_prefix="MCP_", env_file=".env.remote")

    def __init__(self, **data):
        """Initialize settings with values from environment variables."""
        super().__init__(**data)
        self.callback_path = urljoin(self.server_url.unicode_string(), "callback")
        self.singlestore_auth_url, self.singlestore_token_url = (
            self.discover_oauth_server()
        )
        self.analytics_manager = AnalyticsManager(self.segment_write_key)

    def discover_oauth_server(self) -> tuple[str, str]:
        """Discover OAuth server endpoints"""
        discovery_url = f"{self.issuer_url}/.well-known/openid-configuration"
        response = requests.get(discovery_url, timeout=10)
        response.raise_for_status()

        authorization_endpoint: str = response.json().get("authorization_endpoint")

        if not authorization_endpoint:
            raise ValueError("Failed to discover OAuth endpoints")

        token_endpoint: str = response.json().get("token_endpoint")
        if not token_endpoint:
            raise ValueError("Failed to discover OAuth endpoints")

        return authorization_endpoint, token_endpoint


# Context variable to store the Settings instance
_settings_ctx: ContextVar[Settings] = ContextVar("settings", default=None)

# Context variable to store the user_id for the session
_user_id_ctx: ContextVar[str | None] = ContextVar("user_id", default=None)


def set_user_id(user_id: str):
    """Set the user_id for the current session."""
    _user_id_ctx.set(user_id)


def get_user_id() -> str | None:
    """Get the user_id for the current session, or None if not set."""
    return _user_id_ctx.get()


def init_settings(
    transport: Transport, api_key: str | None = None
) -> RemoteSettings | LocalSettings:
    match transport:
        case Transport.HTTP:
            settings = RemoteSettings(transport=Transport.HTTP)
        case Transport.SSE:
            settings = RemoteSettings(transport=Transport.SSE)
        case Transport.STDIO:
            settings = LocalSettings(api_key=api_key)
        case _:
            raise ValueError(f"Unsupported transport mode: {transport}")

    _settings_ctx.set(settings)
    return settings


def get_settings() -> RemoteSettings | LocalSettings:
    settings = _settings_ctx.get()
    if settings is None:
        raise RuntimeError("Settings have not been initialized.")
    return settings


# Context variable to store the app instance
_app_ctx: ContextVar[FastMCP] = ContextVar("app", default=None)


def get_app() -> FastMCP:
    app = _app_ctx.get()
    if app is None:
        raise RuntimeError("App has not been initialized.")
    return app


def get_session_request() -> Request:
    """
    Retrieve the session request from the app context.
    Returns:
        Request: The current session's request object
    """
    app = get_app()
    return cast(Request, app.get_context()._request_context.request)
