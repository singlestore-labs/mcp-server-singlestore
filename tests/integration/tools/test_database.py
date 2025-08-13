import pytest
import pytest_asyncio
import random
import string
from src.api.tools.database.database import run_sql, create_pipeline
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
class TestDatabase:
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

    @pytest.mark.asyncio
    async def test_create_pipeline_with_csv_data(self, workspace_fixture):
        """Test creating a pipeline that loads CSV data from S3."""
        ctx, workspace_id, database_name, username, password = workspace_fixture

        # Create the target table with proper schema
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS uk_price_paid (
           price BIGINT,
           date Date,
           postcode VARCHAR(100),
           type ENUM('terraced', 'semi-detached', 'detached', 'flat', 'other'),
           is_new BOOL,
           duration ENUM('freehold', 'leasehold', 'unknown'),
           addr1 VARCHAR(100),
           addr2 VARCHAR(100),
           street VARCHAR(100),
           locality VARCHAR(100),
           town VARCHAR(100),
           district VARCHAR(100),
           county VARCHAR(100)
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

        # Create the stored procedure to process the CSV data
        create_procedure_sql = """
        CREATE OR REPLACE PROCEDURE process_uk_price_paid (
           _batch QUERY(
             uuid TEXT NOT NULL,
             price TEXT NOT NULL,
             date TEXT NOT NULL,
             postcode TEXT NOT NULL,
             type TEXT NOT NULL,
             is_new TEXT NOT NULL,
             duration TEXT NOT NULL,
             addr1 TEXT NOT NULL,
             addr2 TEXT NOT NULL,
             street TEXT NOT NULL,
             locality TEXT NOT NULL,
             town TEXT NOT NULL,
             district TEXT NOT NULL,
             county TEXT NOT NULL,
             val1 TEXT NOT NULL,
             val2 TEXT NOT NULL
           )
         )
         AS
         BEGIN
           INSERT INTO uk_price_paid (
             price,
             date,
             postcode,
             type,
             is_new,
             duration,
             addr1,
             addr2,
             street,
             locality,
             town,
             district,
             county
           )
           SELECT
             price,
             date,
             postcode,
             CASE
               WHEN type = 'T' THEN 'terraced'
               WHEN type = 'S' THEN 'semi-detached'
               WHEN type = 'D' THEN 'detached'
               WHEN type = 'F' THEN 'flat'
               WHEN type = 'O' THEN 'other'
               ELSE 'other'
             END AS type,
             CASE
               WHEN is_new = 'Y' THEN TRUE
               ELSE FALSE
             END AS is_new,
             CASE
               WHEN duration = 'F' THEN 'freehold'
               WHEN duration = 'L' THEN 'leasehold'
               WHEN duration = 'U' THEN 'unknown'
               ELSE 'unknown'
             END AS duration,
             addr1,
             addr2,
             street,
             locality,
             town,
             district,
             county
           FROM _batch;
         END
        """

        result = await run_sql(
            ctx=ctx,
            sql_query=create_procedure_sql,
            id=workspace_id,
            database=database_name,
            username=username,
            password=password,
        )
        assert result["status"] == "success"

        # Create pipeline using the procedure
        pipeline_name = random_name("uk_price_paid_pipeline")
        data_source = "s3://singlestore-docs-example-datasets/pp-monthly/pp-monthly-update-new-version.csv"

        result = await create_pipeline(
            ctx=ctx,
            pipeline_name=pipeline_name,
            data_source=data_source,
            target_table_or_procedure="process_uk_price_paid",
            workspace_id=workspace_id,
            database=database_name,
            credentials="{}",
            username=username,
            password=password,
        )

        assert result["status"] == "success"
        assert result["data"]["pipelineName"] == pipeline_name
        assert result["data"]["dataSource"] == data_source
        assert result["data"]["targetTableOrProcedure"] == "process_uk_price_paid"
        assert result["data"]["autoStarted"] is True

        # Wait a moment for pipeline to process some data
        import asyncio

        await asyncio.sleep(5)

        # Check that data was loaded
        select_sql = "SELECT COUNT(*) as record_count FROM uk_price_paid"
        result = await run_sql(
            ctx=ctx,
            sql_query=select_sql,
            id=workspace_id,
            database=database_name,
            username=username,
            password=password,
        )

        assert result["status"] == "success"
        record_count = result["data"]["result"][0]["record_count"]
        assert record_count > 0, (
            f"Expected some records to be loaded, but got {record_count}"
        )

        # Check sample data structure
        sample_sql = "SELECT * FROM uk_price_paid LIMIT 3"
        result = await run_sql(
            ctx=ctx,
            sql_query=sample_sql,
            id=workspace_id,
            database=database_name,
            username=username,
            password=password,
        )

        assert result["status"] == "success"
        rows = result["data"]["result"]
        assert len(rows) > 0

        # Verify data structure - check that we have expected columns
        first_row = rows[0]
        expected_columns = [
            "price",
            "date",
            "postcode",
            "type",
            "is_new",
        ]
        for col in expected_columns:
            assert col in first_row, f"Expected column '{col}' not found in data"

        # Verify data types and transformations
        assert isinstance(first_row["price"], int)
        assert first_row["type"] in [
            "terraced",
            "semi-detached",
            "detached",
            "flat",
            "other",
        ]

        # Stop the pipeline
        stop_sql = f"STOP PIPELINE {pipeline_name}"
        result = await run_sql(
            ctx=ctx,
            sql_query=stop_sql,
            id=workspace_id,
            database=database_name,
            username=username,
            password=password,
        )
        assert result["status"] == "success"

        # Drop the pipeline
        drop_sql = f"DROP PIPELINE {pipeline_name}"
        result = await run_sql(
            ctx=ctx,
            sql_query=drop_sql,
            id=workspace_id,
            database=database_name,
            username=username,
            password=password,
        )
        assert result["status"] == "success"
