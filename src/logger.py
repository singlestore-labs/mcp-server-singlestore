"""
Centralized logging configuration for MCP Server.

This module provides a unified logging system for the entire MCP Server project.
All modules should use this centralized logger instead of creating their own.

Usage:
    Basic usage in any module:
    ```python
    from .logger import get_logger
    logger = get_logger()

    logger.info("This is an info message")
    logger.debug("This is a debug message")
    logger.warning("This is a warning")
    logger.error("This is an error")
    ```

Configuration:
    The logger behavior is controlled by the LOG_LEVEL environment variable:

    - LOG_LEVEL=DEBUG: Shows all messages with detailed timestamps and function info
    - LOG_LEVEL=INFO: Shows info, warning, and error messages (default)
    - LOG_LEVEL=WARNING: Shows only warning and error messages
    - LOG_LEVEL=ERROR: Shows only error messages

    Examples:
    ```bash
    # Default (INFO level)
    python your_script.py

    # Debug mode with detailed output
    LOG_LEVEL=DEBUG python your_script.py

    # Quiet mode (warnings and errors only)
    LOG_LEVEL=WARNING python your_script.py
    ```

Logger Name:
    All loggers use the name "MCP_SERVER" for consistency across the project.
"""

import os
import logging
from typing import Optional

# Logger name for the entire project
LOGGER_NAME = "MCP_SERVER"

# Default log level
DEFAULT_LOG_LEVEL = "INFO"

# Available log levels
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# Keep track of whether logger is already configured
_logger_configured = False


def get_log_level() -> int:
    """
    Get the log level from environment variable.

    Returns:
        Log level integer value
    """
    log_level_str = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    return LOG_LEVELS.get(log_level_str, logging.INFO)


def setup_logger(
    name: Optional[str] = None, force_reconfigure: bool = False
) -> logging.Logger:
    """
    Set up and configure the project logger.

    Args:
        name: Optional logger name, defaults to LOGGER_NAME
        force_reconfigure: Force reconfiguration even if already set up

    Returns:
        Configured logger instance
    """
    global _logger_configured

    logger_name = name or LOGGER_NAME
    logger = logging.getLogger(logger_name)

    # Avoid duplicate handlers if logger is already configured and not forcing
    if _logger_configured and not force_reconfigure:
        return logger

    # Clear existing handlers if reconfiguring
    if force_reconfigure:
        logger.handlers.clear()

    # Get log level from environment
    log_level = get_log_level()

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    # Create formatter based on log level
    if log_level == logging.DEBUG:
        # Detailed format for debug mode
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        )
    else:
        # Simple format for other levels
        formatter = logging.Formatter("%(levelname)s: %(message)s")

    console_handler.setFormatter(formatter)

    # Configure logger
    logger.addHandler(console_handler)
    logger.setLevel(log_level)

    # Prevent propagation to avoid duplicate logs
    logger.propagate = False

    _logger_configured = True
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance for the project.

    Args:
        name: Optional logger name, defaults to LOGGER_NAME

    Returns:
        Logger instance
    """
    logger_name = name or LOGGER_NAME

    # Check if logger exists and is configured
    logger = logging.getLogger(logger_name)
    if not logger.handlers:
        # Logger not configured yet, set it up
        return setup_logger(logger_name)

    return logger


# Create the main project logger on import
logger = setup_logger()
