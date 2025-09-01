import pytest
import src.api.tools as tools


@pytest.mark.integration
class TestUserInfoIntegration:
    """Integration tests for get_user_info tool that make actual API calls."""

    @pytest.mark.asyncio
    async def test_get_user_info(self, mock_context):
        """
        Test get_user_info tool with actual API key authentication.

        This test makes real API calls to the SingleStore Management API
        using the MCP_API_KEY environment variable.
        """
        result = tools.get_user_info(ctx=mock_context)

        assert result["status"] == "success"
        assert "data" in result

        data = result["data"]

        assert "result" in data

        user_data = data["result"]

        # User data should contain userID, email, firstName, lastName
        assert "userID" in user_data
        assert "email" in user_data
        assert "firstName" in user_data
        assert "lastName" in user_data

        assert user_data["userID"] is not None
        assert user_data["email"] is not None
        assert user_data["firstName"] is not None
        assert user_data["lastName"] is not None

        assert user_data["firstName"] == "Pedro"
        assert user_data["lastName"] == "Rodrigues"
