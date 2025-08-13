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
async def workspace_fixture(mock_context):
    ctx = mock_context
    workspace_name = random_name("testws")
    database_name = random_name("testdb")

    # Get available regions first
    regions = build_request("GET", "regions/sharedtier")
    if not regions:
        raise ValueError("No shared tier regions available")

    # Use the first available region
    first_region = regions[0]

    # Create starter workspace
    payload = {
        "name": workspace_name,
        "databaseName": database_name,
        "provider": first_region.get("provider"),
        "regionName": first_region.get("regionName"),
    }
    starter_workspace_data = build_request(
        "POST", "sharedtier/virtualWorkspaces", data=payload
    )
    workspace_id = starter_workspace_data.get("virtualWorkspaceID")
    database_name = starter_workspace_data.get("databaseName")
    assert workspace_id is not None

    # Create a user for the starter workspace
    username = random_name("testuser")
    user_payload = {
        "userName": username,
    }
    user_data = build_request(
        "POST", f"sharedtier/virtualWorkspaces/{workspace_id}/users", data=user_payload
    )
    user_id = user_data.get("userID")
    user_password = user_data.get("password")
    assert user_id is not None
    assert user_password is not None

    yield ctx, workspace_id, database_name, username, user_password

    # Cleanup: delete the starter workspace
    try:
        build_request("DELETE", f"sharedtier/virtualWorkspaces/{workspace_id}")
    except Exception:
        pass  # Ignore cleanup errors


@pytest.mark.integration
class TestRunSQLVirtualWorkspace:
    @pytest.mark.asyncio
    async def test_run_sql_on_virtual_workspace(self, workspace_fixture):
        """Test creating a table and inserting/selecting data."""
        ctx, workspace_id, database_name, username, password = workspace_fixture

        # Create a test table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS test_table (
            id INT PRIMARY KEY,
            name VARCHAR(100),
            value DECIMAL(10,2)
        )
        """

        result = await run_sql(
            ctx=ctx,
            sql_query=create_table_sql,
            id=workspace_id,
            database=database_name,
            username=username,
            password=password,
        )
        assert result["status"] == "success"

        # Insert test data
        insert_sql = """
        INSERT INTO test_table (id, name, value) VALUES
        (1, 'test_item_1', 10.50),
        (2, 'test_item_2', 25.75)
        """

        result = await run_sql(
            ctx=ctx,
            sql_query=insert_sql,
            id=workspace_id,
            database=database_name,
            username=username,
            password=password,
        )
        assert result["status"] == "success"

        # Select and verify data
        select_sql = "SELECT id, name, value FROM test_table ORDER BY id"

        result = await run_sql(
            ctx=ctx,
            sql_query=select_sql,
            id=workspace_id,
            database=database_name,
            username=username,
            password=password,
        )

        assert result["status"] == "success"
        assert result["data"]["row_count"] == 2

        # Verify the data content
        rows = result["data"]["result"]
        assert rows[0]["id"] == 1
        assert rows[0]["name"] == "test_item_1"
        assert float(rows[0]["value"]) == 10.50

        assert rows[1]["id"] == 2
        assert rows[1]["name"] == "test_item_2"
        assert float(rows[1]["value"]) == 25.75
