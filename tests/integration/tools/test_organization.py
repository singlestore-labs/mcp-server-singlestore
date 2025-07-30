"""Integration tests for organization tools."""

import pytest
from src.api.tools.organization.organization import organization_info


@pytest.mark.integration
class TestOrganizationInfoIntegration:
    """Integration tests for organization_info tool that make actual API calls."""

    def test_organization_info(self):
        """
        Test organization_info tool with actual API key authentication.

        This test makes real API calls to the SingleStore Management API
        using the MCP_API_KEY environment variable.
        """

        # Call the organization_info function
        result = organization_info()

        assert "data" in result

        # Verify the data structure
        data = result["data"]
        assert "result" in data
        org_data = data["result"]

        # Organization data should contain orgID and name
        assert "orgID" in org_data
        assert "name" in org_data
        assert org_data["orgID"] is not None
        assert org_data["name"] is not None
        print(f"Organization ID: {org_data['orgID']}, Name: {org_data['name']}")
