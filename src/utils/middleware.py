from functools import wraps
from typing import Callable, Any, Dict, Optional
from src.auth import get_authentication_token, refresh_token, load_credentials, TokenSet
from src.config.app_config import app_config, AuthMethod

def auth_middleware(func: Callable) -> Callable:
    """
    Authentication middleware that automatically handles authentication for tools.
    
    This middleware will:
    1. Check if an authentication token exists
    2. If not, attempt to authenticate
    3. If the token is expired, attempt to refresh
    4. If refresh fails, attempt to authenticate again
    5. Call the wrapped function with the authenticated token
    
    Args:
        func: The function to wrap
        
    Returns:
        Wrapped function that automatically handles authentication
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Check if we already have a valid token
        current_token = app_config.get_auth_token()
        
        # If no token, authenticate
        if not current_token:
            print("No authentication token found. Attempting to authenticate...")
            current_token = get_authentication_token()
            
            if current_token:
                app_config.set_auth_token(current_token, AuthMethod.JWT_TOKEN)
            else:
                # If authentication failed, return error
                return {
                    "status": "error",
                    "message": "Authentication failed. Please try again or provide an API key."
                }
        
        # If token might be expired, check if we need to refresh
        credentials = load_credentials()
        if app_config.get_auth_method() == AuthMethod.JWT_TOKEN and credentials and "token_set" in credentials:
            token_set = TokenSet(credentials["token_set"])
            
            # If token is expired, try to refresh it
            if token_set.is_expired():
                print("Authentication token expired. Attempting to refresh...")
                refreshed_token_set = refresh_token(token_set)
                
                if refreshed_token_set and refreshed_token_set.access_token:
                    print("Successfully refreshed authentication token.")
                    app_config.set_auth_token(refreshed_token_set.access_token, AuthMethod.JWT_TOKEN)
                else:
                    # If refresh failed, try to authenticate again
                    print("Token refresh failed. Attempting to re-authenticate...")
                    current_token = get_authentication_token()
                    
                    if current_token:
                        app_config.set_auth_token(current_token, AuthMethod.JWT_TOKEN)
                    else:
                        # If authentication failed, return error
                        return {
                            "status": "error",
                            "message": "Authentication failed. Please try again or provide an API key."
                        }
        
        # Now that we have a valid token, call the original function
        return func(*args, **kwargs)
        
    return wrapper


def apply_auth_middleware(tools: list) -> list:
    """
    Apply authentication middleware to a list of tools.
    
    This function will wrap each tool function with the auth_middleware,
    except for login and refresh_auth_token tools.
    
    Args:
        tools: List of tool objects
        
    Returns:
        List of tools with auth middleware applied
    """
    # List of tools that should not have auth middleware applied
    excluded_tools = ["login", "refresh_auth_token"]
    
    for tool in tools:
        # Skip the login and refresh_auth_token tools
        if tool.name not in excluded_tools:
            # Apply middleware to the function
            tool.func = auth_middleware(tool.func)
    
    return tools
