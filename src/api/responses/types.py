"""
Standardized response types for SingleStore MCP Server tools.

This module provides a unified response structure for all tool functions,
ensuring consistency and better error handling across the codebase.
"""

from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum
import logging

logger = logging.getLogger("MCP_SERVER")


class ResponseStatus(str, Enum):
    """Standard response status codes."""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PARTIAL = "partial"


class ToolResponse(BaseModel):
    """Standardized response format for all MCP tools."""

    # Core fields (always present)
    status: ResponseStatus = Field(description="Operation status")
    message: str = Field(description="Human-readable result description")

    # Data payload (optional, tool-specific)
    data: Optional[Dict[str, Any]] = Field(
        default=None, description="Tool-specific response data"
    )

    # Metadata (optional)
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional context and metrics"
    )

    # Error details (only for error status)
    error_code: Optional[str] = Field(
        default=None, description="Machine-readable error identifier"
    )
    error_details: Optional[Dict[str, Any]] = Field(
        default=None, description="Detailed error information"
    )

    # Pagination (for list responses)
    pagination: Optional[Dict[str, Union[int, str, bool]]] = Field(
        default=None, description="Pagination information for list responses"
    )


class ResourceResponse(BaseModel):
    """Standardized response format for MCP resources."""

    status: ResponseStatus
    message: str
    content: Optional[str] = None
    uri: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class PromptResponse(BaseModel):
    """Standardized response format for MCP prompts."""

    status: ResponseStatus
    message: str
    content: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class ToolResponseBuilder:
    """Builder pattern for creating standardized responses."""

    @staticmethod
    def success(
        message: str,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        pagination: Optional[Dict[str, Union[int, str, bool]]] = None,
    ) -> ToolResponse:
        """Create a successful response."""
        return ToolResponse(
            status=ResponseStatus.SUCCESS,
            message=message,
            data=data,
            metadata=metadata,
            pagination=pagination,
        )

    @staticmethod
    def error(
        message: str,
        error_code: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> ToolResponse:
        """Create an error response."""
        return ToolResponse(
            status=ResponseStatus.ERROR,
            message=message,
            error_code=error_code,
            error_details=error_details,
            data=data,
        )

    @staticmethod
    def warning(
        message: str,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ToolResponse:
        """Create a warning response."""
        return ToolResponse(
            status=ResponseStatus.WARNING, message=message, data=data, metadata=metadata
        )

    @staticmethod
    def partial(
        message: str,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ToolResponse:
        """Create a partial success response."""
        return ToolResponse(
            status=ResponseStatus.PARTIAL, message=message, data=data, metadata=metadata
        )

    @staticmethod
    def from_legacy(result: Any, function_name: str) -> ToolResponse:
        """Convert legacy return values to standardized responses."""

        # If already a ToolResponse, return as-is
        if isinstance(result, ToolResponse):
            return result

        # If already a dict with status, convert to standardized format
        if isinstance(result, dict) and "status" in result:
            status = result.get("status", "success").lower()

            if status == "error":
                return ToolResponseBuilder.error(
                    message=result.get("message", f"{function_name} failed"),
                    error_code=result.get("error_code"),
                    error_details=result.get("error_details")
                    or {"error": result.get("error"), "original_response": result},
                    data={
                        k: v
                        for k, v in result.items()
                        if k
                        not in (
                            "status",
                            "message",
                            "error_code",
                            "error_details",
                            "error",
                        )
                    },
                )
            elif status == "warning":
                return ToolResponseBuilder.warning(
                    message=result.get(
                        "message", f"{function_name} completed with warnings"
                    ),
                    data={
                        k: v
                        for k, v in result.items()
                        if k not in ("status", "message")
                    },
                )
            else:
                return ToolResponseBuilder.success(
                    message=result.get(
                        "message", f"{function_name} completed successfully"
                    ),
                    data={
                        k: v
                        for k, v in result.items()
                        if k not in ("status", "message")
                    },
                )

        # Handle different return types
        if isinstance(result, dict):
            return ToolResponseBuilder.success(
                message=f"{function_name} completed successfully", data=result
            )
        elif isinstance(result, (list, tuple)):
            return ToolResponseBuilder.success(
                message=f"{function_name} returned {len(result)} items",
                data={"items": result},
                metadata={"count": len(result)},
            )
        elif isinstance(result, str):
            return ToolResponseBuilder.success(
                message=f"{function_name} completed", data={"result": result}
            )
        else:
            return ToolResponseBuilder.success(
                message=f"{function_name} completed", data={"result": result}
            )


class ResourceResponseBuilder:
    """Builder for creating standardized resource responses."""

    @staticmethod
    def success(
        content: str,
        uri: str,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ResourceResponse:
        """Create a successful resource response."""
        from datetime import datetime, timezone

        return ResourceResponse(
            status=ResponseStatus.SUCCESS,
            message=message or f"Resource retrieved successfully from {uri}",
            content=content,
            uri=uri,
            metadata={
                **(metadata or {}),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "content_length": len(content) if content else 0,
            },
        )

    @staticmethod
    def error(
        message: str,
        uri: Optional[str] = None,
        error_code: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> ResourceResponse:
        """Create an error resource response."""
        from datetime import datetime, timezone

        return ResourceResponse(
            status=ResponseStatus.ERROR,
            message=message,
            uri=uri,
            error_code=error_code,
            error_details=error_details,
            metadata={
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @staticmethod
    def from_legacy(
        legacy_response: Any,
        uri: str,
        function_name: str = "resource_function",
    ) -> ResourceResponse:
        """Convert legacy resource response to standardized format."""
        try:
            if isinstance(legacy_response, str):
                return ResourceResponseBuilder.success(
                    content=legacy_response,
                    uri=uri,
                    message=f"Resource content retrieved from {uri}",
                )
            elif isinstance(legacy_response, dict):
                content = legacy_response.get("content", str(legacy_response))
                return ResourceResponseBuilder.success(
                    content=content,
                    uri=uri,
                    metadata={"legacy_data": legacy_response},
                )
            else:
                return ResourceResponseBuilder.success(
                    content=str(legacy_response), uri=uri
                )
        except Exception as e:
            return ResourceResponseBuilder.error(
                message=f"Failed to process resource response: {str(e)}",
                uri=uri,
                error_code=type(e).__name__,
                error_details={"exception": str(e)},
            )


class PromptResponseBuilder:
    """Builder for creating standardized prompt responses."""

    @staticmethod
    def success(
        content: str,
        message: Optional[str] = None,
        arguments: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PromptResponse:
        """Create a successful prompt response."""
        from datetime import datetime, timezone

        return PromptResponse(
            status=ResponseStatus.SUCCESS,
            message=message or "Prompt generated successfully",
            content=content,
            arguments=arguments,
            metadata={
                **(metadata or {}),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "content_length": len(content) if content else 0,
            },
        )

    @staticmethod
    def error(
        message: str,
        error_code: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> PromptResponse:
        """Create an error prompt response."""
        from datetime import datetime, timezone

        return PromptResponse(
            status=ResponseStatus.ERROR,
            message=message,
            arguments=arguments,
            error_code=error_code,
            error_details=error_details,
            metadata={
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @staticmethod
    def from_legacy(
        legacy_response: Any,
        function_name: str = "prompt_function",
        arguments: Optional[Dict[str, Any]] = None,
    ) -> PromptResponse:
        """Convert legacy prompt response to standardized format."""
        try:
            if isinstance(legacy_response, str):
                return PromptResponseBuilder.success(
                    content=legacy_response,
                    arguments=arguments,
                    message=f"Prompt content generated by {function_name}",
                )
            elif isinstance(legacy_response, dict):
                content = legacy_response.get("content", str(legacy_response))
                return PromptResponseBuilder.success(
                    content=content,
                    arguments=arguments,
                    metadata={"legacy_data": legacy_response},
                )
            else:
                return PromptResponseBuilder.success(
                    content=str(legacy_response), arguments=arguments
                )
        except Exception as e:
            return PromptResponseBuilder.error(
                message=f"Failed to process prompt response: {str(e)}",
                error_code=type(e).__name__,
                error_details={"exception": str(e)},
                arguments=arguments,
            )
