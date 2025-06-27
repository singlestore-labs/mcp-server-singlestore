"""
Tests for response standardization system.
"""

from src.api.responses import (
    ResponseStatus,
    ToolResponse,
    ToolResponseBuilder,
    standardize_response,
    convert_to_dict,
    tool_response,
)


class TestToolResponse:
    """Test ToolResponse model."""

    def test_success_response_creation(self):
        """Test creating a success response."""
        response = ToolResponse(
            status=ResponseStatus.SUCCESS,
            message="Operation completed",
            data={"result": "test"},
        )

        assert response.status == ResponseStatus.SUCCESS
        assert response.message == "Operation completed"
        assert response.data == {"result": "test"}
        assert response.error_code is None
        assert response.error_details is None

    def test_error_response_creation(self):
        """Test creating an error response."""
        response = ToolResponse(
            status=ResponseStatus.ERROR,
            message="Operation failed",
            error_code="TEST_ERROR",
            error_details={"cause": "test failure"},
        )

        assert response.status == ResponseStatus.ERROR
        assert response.message == "Operation failed"
        assert response.error_code == "TEST_ERROR"
        assert response.error_details == {"cause": "test failure"}


class TestToolResponseBuilder:
    """Test ToolResponseBuilder methods."""

    def test_success_builder(self):
        """Test success response builder."""
        response = ToolResponseBuilder.success(
            message="Test successful", data={"items": [1, 2, 3]}, metadata={"count": 3}
        )

        assert response.status == ResponseStatus.SUCCESS
        assert response.message == "Test successful"
        assert response.data == {"items": [1, 2, 3]}
        assert response.metadata == {"count": 3}

    def test_error_builder(self):
        """Test error response builder."""
        response = ToolResponseBuilder.error(
            message="Test failed",
            error_code="VALIDATION_ERROR",
            error_details={"field": "name", "issue": "required"},
        )

        assert response.status == ResponseStatus.ERROR
        assert response.message == "Test failed"
        assert response.error_code == "VALIDATION_ERROR"
        assert response.error_details == {"field": "name", "issue": "required"}

    def test_warning_builder(self):
        """Test warning response builder."""
        response = ToolResponseBuilder.warning(
            message="Test completed with warnings", data={"partial_results": True}
        )

        assert response.status == ResponseStatus.WARNING
        assert response.message == "Test completed with warnings"
        assert response.data == {"partial_results": True}

    def test_from_legacy_dict_with_status(self):
        """Test converting legacy dict response with status."""
        legacy_response = {
            "status": "success",
            "message": "Legacy success",
            "result": "test_data",
        }

        response = ToolResponseBuilder.from_legacy(legacy_response, "test_function")

        assert response.status == ResponseStatus.SUCCESS
        assert response.message == "Legacy success"
        assert response.data == {"result": "test_data"}

    def test_from_legacy_dict_without_status(self):
        """Test converting legacy dict response without status."""
        legacy_response = {"result": "test_data", "count": 5}

        response = ToolResponseBuilder.from_legacy(legacy_response, "test_function")

        assert response.status == ResponseStatus.SUCCESS
        assert response.message == "test_function completed successfully"
        assert response.data == {"result": "test_data", "count": 5}

    def test_from_legacy_list(self):
        """Test converting legacy list response."""
        legacy_response = [1, 2, 3, 4, 5]

        response = ToolResponseBuilder.from_legacy(legacy_response, "test_function")

        assert response.status == ResponseStatus.SUCCESS
        assert response.message == "test_function returned 5 items"
        assert response.data == {"items": [1, 2, 3, 4, 5]}
        assert response.metadata == {"count": 5}

    def test_from_legacy_string(self):
        """Test converting legacy string response."""
        legacy_response = "test result"

        response = ToolResponseBuilder.from_legacy(legacy_response, "test_function")

        assert response.status == ResponseStatus.SUCCESS
        assert response.message == "test_function completed"
        assert response.data == {"result": "test result"}

    def test_from_legacy_error_dict(self):
        """Test converting legacy error dict response."""
        legacy_response = {
            "status": "error",
            "message": "Something went wrong",
            "error": "Invalid input",
            "error_code": "VALIDATION_ERROR",
        }

        response = ToolResponseBuilder.from_legacy(legacy_response, "test_function")

        assert response.status == ResponseStatus.ERROR
        assert response.message == "Something went wrong"
        assert response.error_code == "VALIDATION_ERROR"
        assert "error" in response.error_details


class TestStandardizeResponseDecorator:
    """Test the standardize_response decorator."""

    def test_decorator_with_dict_return(self):
        """Test decorator with function returning dict."""

        @standardize_response
        def test_function():
            return {"result": "success", "count": 3}

        response = test_function()

        assert isinstance(response, ToolResponse)
        assert response.status == ResponseStatus.SUCCESS
        assert response.data == {"result": "success", "count": 3}

    def test_decorator_with_list_return(self):
        """Test decorator with function returning list."""

        @standardize_response
        def test_function():
            return [1, 2, 3]

        response = test_function()

        assert isinstance(response, ToolResponse)
        assert response.status == ResponseStatus.SUCCESS
        assert response.data == {"items": [1, 2, 3]}
        assert response.metadata == {"count": 3}

    def test_decorator_with_exception(self):
        """Test decorator with function raising exception."""

        @standardize_response
        def test_function():
            raise ValueError("Test error")

        response = test_function()

        assert isinstance(response, ToolResponse)
        assert response.status == ResponseStatus.ERROR
        assert "Failed to execute test_function" in response.message
        assert response.error_code == "ValueError"
        assert "Test error" in response.error_details["exception"]

    def test_decorator_with_tool_response_return(self):
        """Test decorator with function returning ToolResponse."""

        @standardize_response
        def test_function():
            return ToolResponseBuilder.success("Already standardized")

        response = test_function()

        assert isinstance(response, ToolResponse)
        assert response.status == ResponseStatus.SUCCESS
        assert response.message == "Already standardized"


class TestConvertToDict:
    """Test convert_to_dict function."""

    def test_convert_success_response(self):
        """Test converting success response to dict."""
        response = ToolResponseBuilder.success(
            message="Test message", data={"key": "value"}, metadata={"count": 1}
        )

        result = convert_to_dict(response)

        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert result["message"] == "Test message"
        assert result["data"] == {"key": "value"}
        assert result["metadata"] == {"count": 1}
        # None fields should be excluded
        assert "error_code" not in result
        assert "error_details" not in result

    def test_convert_error_response(self):
        """Test converting error response to dict."""
        response = ToolResponseBuilder.error(
            message="Error occurred",
            error_code="TEST_ERROR",
            error_details={"field": "test"},
        )

        result = convert_to_dict(response)

        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert result["message"] == "Error occurred"
        assert result["error_code"] == "TEST_ERROR"
        assert result["error_details"] == {"field": "test"}


class TestToolResponseDecorator:
    """Test the tool_response decorator."""

    def test_tool_response_decorator(self):
        """Test decorator that ensures dict return."""

        @tool_response
        def test_function():
            return {"result": "test"}

        result = test_function()

        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert result["data"] == {"result": "test"}

    def test_tool_response_with_exception(self):
        """Test decorator with exception returns dict."""

        @tool_response
        def test_function():
            raise RuntimeError("Test error")

        result = test_function()

        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert "RuntimeError" in result["error_code"]
