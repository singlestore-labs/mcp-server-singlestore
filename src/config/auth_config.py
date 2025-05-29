from enum import Enum
from typing import Optional


class AuthMethod(str, Enum):
    """Authentication method enum"""

    API_KEY = "api_key"
    JWT_TOKEN = "jwt_token"
    OAUTH = "oauth"


class AuthConfig:
    """Authentication configuration class that handles authentication state."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        jwt_token: Optional[str] = None,
        oauth_token: Optional[str] = None,
        token_expiration_interval: int = 3600,
    ):
        # ...existing code from AuthConfig...
        self._api_key = api_key
        self._jwt_token = jwt_token
        self._oauth_token = oauth_token
        self._token_expiration_interval = token_expiration_interval

        auth_methods_count = sum(
            1 for token in [api_key, jwt_token, oauth_token] if token
        )
        if auth_methods_count > 1:
            raise ValueError(
                "Cannot provide multiple authentication tokens. Choose one authentication method."
            )

        if api_key:
            self._auth_method = AuthMethod.API_KEY
        elif jwt_token:
            self._auth_method = AuthMethod.JWT_TOKEN
        elif oauth_token:
            self._auth_method = AuthMethod.OAUTH
        else:
            self._auth_method = None

    # ...rest of AuthConfig unchanged...
    @property
    def auth_method(self) -> Optional[AuthMethod]:
        return self._auth_method

    @auth_method.setter
    def auth_method(self, value: AuthMethod):
        if value not in AuthMethod:
            raise ValueError(f"Invalid authentication method: {value}")
        self._auth_method = value
        if value is None:
            self._api_key = None
            self._jwt_token = None
        elif value == AuthMethod.API_KEY:
            self._jwt_token = None
        elif value == AuthMethod.JWT_TOKEN:
            self._api_key = None

    @property
    def api_key(self) -> Optional[str]:
        return self._api_key

    @api_key.setter
    def api_key(self, value: Optional[str]):
        if value and self._jwt_token:
            self._jwt_token = None
        self._api_key = value
        self._auth_method = AuthMethod.API_KEY if value else None

    @property
    def jwt_token(self) -> Optional[str]:
        return self._jwt_token

    @jwt_token.setter
    def jwt_token(self, value: Optional[str]):
        if value and self._api_key:
            self._api_key = None
        self._jwt_token = value
        self._auth_method = AuthMethod.JWT_TOKEN if value else None

    @property
    def oauth_token(self) -> Optional[str]:
        return self._oauth_token

    @oauth_token.setter
    def oauth_token(self, value: Optional[str]):
        if value:
            self._api_key = None
            self._jwt_token = None
        self._oauth_token = value
        self._auth_method = AuthMethod.OAUTH if value else None

    @property
    def token_expiration_interval(self) -> int:
        return self._token_expiration_interval

    @token_expiration_interval.setter
    def token_expiration_interval(self, value: int):
        if value <= 0:
            raise ValueError("Expiration interval must be a positive integer")
        self._token_expiration_interval = value

    @property
    def auth_token(self) -> Optional[str]:
        if self._auth_method == AuthMethod.API_KEY:
            return self._api_key
        elif self._auth_method == AuthMethod.JWT_TOKEN:
            return self._jwt_token
        elif self._auth_method == AuthMethod.OAUTH:
            return self._oauth_token
        return None

    @auth_token.setter
    def auth_token(self, value: Optional[str]):
        if self._auth_method == AuthMethod.JWT_TOKEN:
            self._jwt_token = value
        elif self._auth_method == AuthMethod.OAUTH:
            self._oauth_token = value
        else:
            self._api_key = value
            self._auth_method = AuthMethod.API_KEY if value else None
