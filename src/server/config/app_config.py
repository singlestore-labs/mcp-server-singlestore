from typing import Optional
from enum import Enum


class AuthMethod(Enum):
    """Authentication method enum"""
    API_KEY = "api_key"
    JWT_TOKEN = "jwt_token"


class AuthConfig:
    """Authentication configuration class that handles authentication state."""
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        jwt_token: Optional[str] = None,
        token_expiration_interval: int = 3600 # Default expiration in seconds
    ):
        """
        Initialize the authentication configuration.
        
        Parameters:
        - api_key: Optional API key for authentication
        - jwt_token: Optional JWT token for authentication
        - token_expiration_interval: JWT token expiration interval in seconds (default: 3600)
        
        Note: User can authenticate with either an API key or JWT token, but not both.
        """
        self._api_key = api_key
        self._jwt_token = jwt_token
        self._token_expiration_interval = token_expiration_interval

        # Determine the authentication method based on provided credentials
        if api_key and jwt_token:
            raise ValueError("Cannot provide both API key and JWT token. Choose one authentication method.")
        
        if api_key:
            self._auth_method = AuthMethod.API_KEY
        elif jwt_token:
            self._auth_method = AuthMethod.JWT_TOKEN
        else:
            self._auth_method = None
    
    @property
    def auth_method(self) -> Optional[AuthMethod]:
        """Get the current authentication method."""
        return self._auth_method
    
    @auth_method.setter
    def auth_method(self, value: AuthMethod):
        """Set the authentication method."""
        if value not in AuthMethod:
            raise ValueError(f"Invalid authentication method: {value}")
        
        self._auth_method = value
        
        # Clear credentials if auth method is set to None
        if value is None:
            self._api_key = None
            self._jwt_token = None
        elif value == AuthMethod.API_KEY:
            self._jwt_token = None
        elif value == AuthMethod.JWT_TOKEN:
            self._api_key = None
    
    @property
    def api_key(self) -> Optional[str]:
        """Get the API key."""
        return self._api_key
    
    @api_key.setter
    def api_key(self, value: Optional[str]):
        """Set the API key and update auth method."""
        if value and self._jwt_token:
            self._jwt_token = None  # Clear JWT token when setting API key
        
        self._api_key = value
        self._auth_method = AuthMethod.API_KEY if value else None
    
    @property
    def jwt_token(self) -> Optional[str]:
        """Get the JWT token."""
        return self._jwt_token
    
    @jwt_token.setter
    def jwt_token(self, value: Optional[str]):
        """Set the JWT token and update auth method."""
        if value and self._api_key:
            self._api_key = None  # Clear API key when setting JWT token
        
        self._jwt_token = value
        self._auth_method = AuthMethod.JWT_TOKEN if value else None
    
    @property
    def token_expiration_interval(self) -> int:
        """Get the token expiration interval in seconds."""
        return self._token_expiration_interval
    
    @token_expiration_interval.setter
    def token_expiration_interval(self, value: int):
        """Set the token expiration interval."""
        if value <= 0:
            raise ValueError("Expiration interval must be a positive integer")
        self._token_expiration_interval = value
    
    @property
    def auth_token(self) -> Optional[str]:
        """
        Get the authentication token (either API key or JWT token) based on the current auth method.
        """
        if self._auth_method == AuthMethod.API_KEY:
            return self._api_key
        elif self._auth_method == AuthMethod.JWT_TOKEN:
            return self._jwt_token
        return None
    
    @auth_token.setter
    def auth_token(self, value: Optional[str]):
        """
        Set the authentication token based on the current auth method.
        If no method is set, defaults to API key.
        """
        if self._auth_method == AuthMethod.JWT_TOKEN:
            self._jwt_token = value
        else:  # Default to API key if no method or API_KEY method
            self._api_key = value
            self._auth_method = AuthMethod.API_KEY if value else None


class OrganizationConfig:
    """Organization configuration class that stores organization-related information."""
    
    def __init__(
        self,
        organization_id: Optional[str] = None,
        organization_name: Optional[str] = None
    ):
        """
        Initialize the organization configuration.
        
        Parameters:
        - organization_id: ID of the selected organization
        - organization_name: Name of the selected organization
        """
        self._organization_id = organization_id
        self._organization_name = organization_name
    
    @property
    def organization_id(self) -> Optional[str]:
        """Get the currently selected organization ID."""
        return self._organization_id
    
    @organization_id.setter
    def organization_id(self, value: Optional[str]):
        """Set the currently selected organization ID."""
        self._organization_id = value
    
    @property
    def organization_name(self) -> Optional[str]:
        """Get the currently selected organization name."""
        return self._organization_name
    
    @organization_name.setter
    def organization_name(self, value: Optional[str]):
        """Set the currently selected organization name."""
        self._organization_name = value
    
    def set_organization(self, org_id: str, org_name: str):
        """
        Set both organization ID and name at once.
        
        Parameters:
        - org_id: Organization ID
        - org_name: Organization name
        """
        self._organization_id = org_id
        self._organization_name = org_name
    
    def clear_organization(self):
        """Clear the currently selected organization."""
        self._organization_id = None
        self._organization_name = None
    
    def is_organization_selected(self) -> bool:
        """Check if an organization is selected."""
        return self._organization_id is not None


class AppConfig:
    """
    Application configuration class that holds the internal state of the application.
    """
    
    def __init__(
        self, 
        auth_config: Optional[AuthConfig] = None,
        org_config: Optional[OrganizationConfig] = None,
        log_enabled: bool = False, 
        log_level: str = "INFO",
        debug_mode: bool = False
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
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if value.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
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


# Global configuration instance
app_config = AppConfig()
