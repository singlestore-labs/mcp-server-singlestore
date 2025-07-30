import pytest
import pytest_asyncio
import random
import string
from src.api.tools.database.database import run_sql
from src.api.common import build_request


def random_name(prefix):
    return f"{prefix}_" + "".join(
        random.choices(string.ascii_lowercase + string.digits, k=8)
    )


@pytest_asyncio.fixture
async def workspace_fixture():
    from mcp.server.fastmcp import Context

    ctx = Context()
    workspace_name = random_name("testws")
    database_name = random_name("testdb")

    payload = {
        "name": workspace_name,
        "databaseName": database_name,
    }
    starter_workspace_data = build_request(
        "POST", "sharedtier/virtualWorkspaces", data=payload
    )
    workspace_id = starter_workspace_data.get("virtualWorkspaceID")
    database_name = starter_workspace_data.get("databaseName")
    assert workspace_id is not None

    yield ctx, workspace_id, database_name

    build_request("DELETE", f"sharedtier/virtualWorkspaces/{workspace_id}")


@pytest.mark.integration
class TestRunSQLVirtualWorkspace:
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Skipping integration test for now.")
    async def test_run_sql_on_virtual_workspace(self, workspace_fixture):
        ctx, workspace_id, database_name = workspace_fixture
        sql_query = "SELECT 1 AS test_col"
        result = await run_sql(
            ctx=ctx,
            sql_query=sql_query,
            id=workspace_id,
            database=database_name,
        )
        assert result["status"] == "success"
        assert result["data"]["row_count"] == 1
        assert result["data"]["result"][0]["test_col"] == 1
