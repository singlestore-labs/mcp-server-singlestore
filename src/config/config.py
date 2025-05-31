# config.py

from abc import ABC
from enum import Enum
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

import requests


class Transport(str, Enum):
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"


class Settings(ABC, BaseSettings):
    host: str = "localhost"
    port: int
    org_id: str
    s2_api_base_url: str
    graphql_public_endpoint: str
    transport: Transport = Transport.STDIO
    is_remote: bool = False

    issuer_url: str
    required_scopes: str

    model_config = SettingsConfigDict(env_prefix="MCP_", env_file=".env")

    server_url: AnyHttpUrl | None = None

    client_id: str
    callback_path: AnyHttpUrl | None = None
    # SingleStore OAuth URLs
    singlestore_auth_url: str | None = None
    singlestore_token_url: str | None = None

    # Stores temporarily generated code verifier for PKCE. Will be deleted after use.
    singlestore_code_verifier: str = ""

    def __init__(self, **data):
        """Initialize settings with values from environment variables."""
        super().__init__(**data)

        self.server_url = AnyHttpUrl(f"http://{self.host}:{self.port}")
        self.callback_path = AnyHttpUrl(f"http://{self.host}:{self.port}/callback")

        self.singlestore_auth_url, self.singlestore_token_url = (
            self.discover_oauth_server()
        )

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


class LocalSettings(Settings):
    graphql_public_endpoint: Optional[str] = None
    s2_api_base_url: Optional[str] = None
    transport: Transport = Transport.STDIO
    is_remote: bool = False


class RemoteSettings(Settings):
    host: str
    mode: Transport
    is_remote: bool = True


settings = None


def init_settings(transport: Transport = Transport.STDIO):
    global settings
    if transport == Transport.HTTP:
        settings = RemoteSettings(mode=Transport.HTTP)
    elif transport == Transport.SSE:
        settings = RemoteSettings(mode=Transport.SSE)
    elif transport == Transport.STDIO:
        settings = LocalSettings()
    else:
        raise ValueError(f"Unsupported transport mode: {transport}")
