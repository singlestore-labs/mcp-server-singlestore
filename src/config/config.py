from typing import List, Literal, cast

from abc import ABC
from contextvars import ContextVar
from enum import Enum
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.requests import Request
from src.analytics.manager import AnalyticsManager
from src.auth.proxy_provider import SingleStoreOAuthProxy
from fastmcp.server.auth.oauth_proxy import OAuthProxy
from src.storage.SingleStoreKV import SingleStoreKV
from src.utils.uuid_validation import validate_uuid_string


class Transport(str, Enum):
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "streamable-http"


class Settings(ABC, BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8010
    s2_api_base_url: str = "https://api.singlestore.com"
    graphql_public_endpoint: str = "https://backend.singlestore.com/public"
    transport: Transport
    is_remote: bool


class LocalSettings(Settings):
    jwt_token: str | None = None
    org_id: str | None = None
    api_key: str | None = None
    transport: Transport = Transport.STDIO
    is_remote: Literal[False] = False

    # Environment variable configuration for Docker use cases
    model_config = SettingsConfigDict(env_prefix="MCP_")

    def set_jwt_token(self, token: str) -> None:
        """Set JWT token for authentication (obtained via browser OAuth)"""
        self.jwt_token = token

    analytics_manager: AnalyticsManager = AnalyticsManager(enabled=False)

    @field_validator("org_id", mode="before")
    @classmethod
    def validate_org_id_uuid(cls, v):
        """Validate that org_id is a valid UUID."""
        return validate_uuid_string(v)


class RemoteSettings(Settings):
    org_id: str | None = None
    is_remote: Literal[True] = True
    issuer_url: str
    openid_config_url: str | None = None
    required_scopes: List[str]
    server_url: AnyHttpUrl
    client_id: str
    callback_path: str = "/callback"
    # SingleStore OAuth URLs
    singlestore_auth_url: str | None = None
    singlestore_token_url: str | None = None
    # SingleStore KV instance
    oauth_db_url: str | None = None
    singlestore_kv: SingleStoreKV | None = None
    # Stores temporarily generated code verifier for PKCE. Will be deleted after use.
    singlestore_code_verifier: str = ""
    # Segment analytics write key
    segment_write_key: str
    # Analytics manager instance
    analytics_manager: AnalyticsManager | None = None
    auth_provider: OAuthProxy | None = None
    jwt_signing_key: str | None = None

    model_config = SettingsConfigDict(env_prefix="MCP_", env_file=".env.remote")

    @field_validator("client_id", mode="before")
    @classmethod
    def validate_uuid_fields(cls, v):
        """Validate that org_id and client_id are valid UUIDs."""
        return validate_uuid_string(v)

    def __init__(self, **data):
        """Initialize settings with values from environment variables."""
        super().__init__(**data)
        self.analytics_manager = AnalyticsManager(self.segment_write_key)
        if self.oauth_db_url:
            self.singlestore_kv = SingleStoreKV(connection_str=self.oauth_db_url)
        self.auth_provider = SingleStoreOAuthProxy(
            issuer_url=self.issuer_url,
            client_id=self.client_id,
            base_url=self.server_url.unicode_string(),
            valid_scopes=self.required_scopes,
            jwt_signing_key=self.jwt_signing_key,
            redirect_path=self.callback_path,
            client_storage=self.singlestore_kv,
        ).get_provider()


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
    transport: Transport,
    jwt_token: str | None = None,
    org_id: str | None = None,
    host: str | None = None,
) -> RemoteSettings | LocalSettings:
    match transport:
        case Transport.HTTP:
            settings = RemoteSettings(transport=Transport.HTTP)
        case Transport.SSE:
            settings = RemoteSettings(transport=Transport.SSE)
        case Transport.STDIO:
            settings = LocalSettings(jwt_token=jwt_token, org_id=org_id, host=host)
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
