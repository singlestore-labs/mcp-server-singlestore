import pytest
import src.api.tools as tools
import random
import string


def random_name(prefix: str, length: int = 8) -> str:
    """
    Generate a random name with the given prefix, using only alphanumeric characters and underscores.
    """
    chars = string.ascii_letters + string.digits
    suffix = "".join(random.choice(chars) for _ in range(length))
    return f"{prefix}_{suffix}"


@pytest.mark.integration
class TestStarterWorkspacesIntegration:
    """Sequential integration test for starter workspaces lifecycle."""

    @pytest.mark.asyncio
    async def test_starter_workspace_lifecycle(self, mock_context):
        # List available regions (already tested elsewhere, just get one)
        regions_data = await tools.list_sharedtier_regions(ctx=mock_context)
        regions = regions_data["data"]["result"]
        region = regions[0]
        provider = region["provider"]
        region_name = region["regionName"]

        # Create a new starter workspace with random names
        workspace_name = random_name("test_ws")
        database_name = random_name("test_db")
        create_result = await tools.create_starter_workspace(
            ctx=mock_context,
            name=workspace_name,
            database_name=database_name,
            provider=provider,
            region_name=region_name,
        )
        assert create_result["status"] == "success"
        created_workspace_id = create_result["workspace_id"]
        assert created_workspace_id is not None

        # List starter workspaces after creation
        workspaces_after_create = tools.list_starter_workspaces()["data"]["result"]
        workspace_ids_after_create = set(
            w["virtualWorkspaceID"] for w in workspaces_after_create
        )
        assert created_workspace_id in workspace_ids_after_create

        # Terminate the newly created workspace
        terminate_result = await tools.terminate_starter_workspace(
            ctx=mock_context,
            workspace_id=created_workspace_id,
        )
        assert terminate_result["status"] == "success"
        assert terminate_result["workspace_id"] == created_workspace_id

        # List starter workspaces after termination
        workspaces_after_terminate = tools.list_starter_workspaces()["data"]["result"]
        workspace_ids_after_terminate = set(
            w["virtualWorkspaceID"] for w in workspaces_after_terminate
        )
        assert created_workspace_id not in workspace_ids_after_terminate
