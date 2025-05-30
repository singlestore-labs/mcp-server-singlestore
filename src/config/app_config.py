import os
from typing import Optional
from enum import Enum
from pydantic import Field
from pydantic_settings import BaseSettings

from src.config.auth_config import AuthConfig, AuthMethod
from src.config.org_config import OrganizationConfig


class AppSettings(BaseSettings):
    # SingleStore
    singlestore_api_key: Optional[str] = Field(None, env="SINGLESTORE_API_KEY")
    singlestore_org_id: Optional[str] = Field(None, env="SINGLESTORE_ORG_ID")
    singlestore_org_name: str = Field(
        "Default Organization", env="SINGLESTORE_ORG_NAME"
    )
    singlestore_api_base_url: str = "https://api.singlestore.com"
    singlestore_graphql_public_endpoint: str = "https://backend.singlestore.com/public"

    # Auth
    client_id: str = Field("b7dbf19e-d140-4334-bae4-e8cd03614485", env="CLIENT_ID")
    oauth_issuer_url: str = Field(
        "https://authsvc.singlestore.com/", env="OAUTH_ISSUER_URL"
    )
    auth_timeout_seconds: int = 60
    client_uri: str = Field("http://localhost:8000", env="CLIENT_URI")

    # App
    log_enabled: bool = False
    log_level: str = "INFO"
    debug_mode: bool = False
    server_host: str = "localhost"
    server_port: int = 8000
    server_mode: str = "stdio"

    # OAuth/JWT
    token_expiration_interval: int = 3600

    # Root directory of the project
    root_dir: str = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Usage: instantiate once and inject as needed
settings = AppSettings()


class AppConfig:
    """
    Application configuration class that holds the internal state of the application.
    """

    class LogLevel(str, Enum):
        DEBUG = "DEBUG"
        INFO = "INFO"
        WARNING = "WARNING"
        ERROR = "ERROR"
        CRITICAL = "CRITICAL"

    def __init__(
        self,
        auth_config: Optional[AuthConfig] = None,
        org_config: Optional[OrganizationConfig] = None,
        log_enabled: bool = False,
        log_level: str = "INFO",
        server_port: int = 8000,
        debug_mode: bool = False,
    ):
        """
        Initialize application configuration.

        Parameters:
        - auth_config: Authentication configuration
        - org_config: Organization configuration
        - log_enabled: Whether logging is enabled
        - log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        - debug_mode: Whether debug mode is enabled
        """
        self._auth_config = auth_config if auth_config else AuthConfig()
        self._org_config = org_config if org_config else OrganizationConfig()
        self._log_enabled = log_enabled
        self._log_level = log_level
        self._debug_mode = debug_mode
        self._server_port = server_port
        self._server_mode = "stdio"  # Default mode
        self.settings: AppSettings = settings

    @property
    def auth_config(self) -> AuthConfig:
        """Get the authentication configuration."""
        return self._auth_config

    @auth_config.setter
    def auth_config(self, value: AuthConfig):
        """Set the authentication configuration."""
        self._auth_config = value

    @property
    def log_enabled(self) -> bool:
        """Get whether logging is enabled."""
        return self._log_enabled

    @log_enabled.setter
    def log_enabled(self, value: bool):
        """Set whether logging is enabled."""
        self._log_enabled = value

    @property
    def log_level(self) -> str:
        """Get the logging level."""
        return self._log_level

    @log_level.setter
    def log_level(self, value: str):
        """Set the logging level."""

        try:
            value = AppConfig.LogLevel(value.upper())
        except ValueError:
            raise ValueError(
                f"Log level must be one of: {', '.join([level.value for level in AppConfig.LogLevel])}"
            )
        self._log_level = value.value
        self._log_level = value.upper()

    @property
    def debug_mode(self) -> bool:
        """Get whether debug mode is enabled."""
        return self._debug_mode

    @debug_mode.setter
    def debug_mode(self, value: bool):
        """Set whether debug mode is enabled."""
        self._debug_mode = value

    @property
    def organization_id(self) -> Optional[str]:
        """Get the currently selected organization ID."""
        return self._org_config.organization_id

    @organization_id.setter
    def organization_id(self, value: Optional[str]):
        """Set the currently selected organization ID."""
        self._org_config.organization_id = value

    @property
    def organization_name(self) -> Optional[str]:
        """Get the currently selected organization name."""
        return self._org_config.organization_name

    @organization_name.setter
    def organization_name(self, value: Optional[str]):
        """Set the currently selected organization name."""
        self._org_config.organization_name = value

    def set_organization(self, org_id: str, org_name: str):
        """
        Set both organization ID and name at once.

        Parameters:
        - org_id: Organization ID
        - org_name: Organization name
        """
        self._org_config.set_organization(org_id, org_name)

    def get_organization(self) -> Optional[tuple[str]]:
        """
        Get the currently selected organization ID and name.

        Returns:
        - Tuple of (organization ID, organization name)
        """
        return self._org_config.get_organization()

    def clear_organization(self):
        """Clear the currently selected organization."""
        self._org_config.clear_organization()

    def is_organization_selected(self) -> bool:
        """Check if an organization is selected."""
        return self._org_config.is_organization_selected()

    def get_auth_method(self) -> Optional[AuthMethod]:
        """Get the authentication method."""
        return self._auth_config.auth_method

    def get_auth_token(self) -> Optional[str]:
        """Get the authentication token from the auth configuration."""
        return self._auth_config.auth_token

    def set_auth_token(self, token: str, method: AuthMethod):
        """
        Set the authentication token with specified method.

        Parameters:
        - token: Authentication token value
        - method: Authentication method
        """
        self._auth_config.auth_method = method
        self._auth_config.auth_token = token

    def get_server_port(self) -> int:
        """Get the server port."""
        return self._server_port

    def set_server_port(self, port: int):
        """Set the server port."""
        if port <= 0 or port > 65535:
            raise ValueError("Port must be between 1 and 65535")
        self._server_port = port

    @property
    def server_mode(self) -> str:
        """Get the server mode."""
        return self._server_mode

    @server_mode.setter
    def server_mode(self, mode: str):
        """Set the server mode."""
        valid_modes = ["stdio", "sse", "http"]
        if mode not in valid_modes:
            raise ValueError(f"Server mode must be one of: {', '.join(valid_modes)}")
        self._server_mode = mode


# Global configuration instance
app_config = AppConfig(
    auth_config=AuthConfig(
        api_key=settings.singlestore_api_key,
        jwt_token=None,
        oauth_token=None,
        token_expiration_interval=settings.token_expiration_interval,
    ),
    org_config=OrganizationConfig(
        organization_id=settings.singlestore_org_id,
        organization_name=settings.singlestore_org_name,
    ),
    log_enabled=settings.log_enabled,
    log_level=settings.log_level,
    server_port=settings.server_port,
    debug_mode=settings.debug_mode,
)

if settings.singlestore_org_id:
    print(
        f"Using organization ID from environment variable SINGLESTORE_ORG_ID: {settings.singlestore_org_id}"
    )
    app_config.set_organization(
        settings.singlestore_org_id, settings.singlestore_org_name
    )
    print(app_config.get_organization())
