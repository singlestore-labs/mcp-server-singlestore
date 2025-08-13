"""Unit tests for the create_pipeline function."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.api.tools.database.database import create_pipeline


@pytest.mark.asyncio
async def test_create_pipeline_sql_generation():
    """Test that create_pipeline generates correct SQL statements."""
    # Mock context
    ctx = AsyncMock()
    ctx.info = AsyncMock()

    # Mock run_sql to return success responses
    mock_run_sql_success = AsyncMock(return_value={"status": "success"})

    with patch("src.api.tools.database.database.run_sql", mock_run_sql_success):
        with patch("src.api.tools.database.database.config") as mock_config:
            # Mock settings and user_id
            mock_settings = MagicMock()
            mock_settings.analytics_manager.track_event = MagicMock()
            mock_config.get_settings.return_value = mock_settings
            mock_config.get_user_id.return_value = "test-user"

            # Test basic pipeline creation
            result = await create_pipeline(
                ctx=ctx,
                pipeline_name="test_pipeline",
                data_source="s3://test-bucket/data.csv",
                target_table_or_procedure="test_table",
                workspace_id="ws-12345678-1234-5678-1234-567812345678",
                database="test_db",
                file_format="CSV",
                credentials="{}",
                config_options='{"region": "us-east-1"}',
                auto_start=True,
            )

            # Verify the result
            assert result["status"] == "success"
            assert result["data"]["pipelineName"] == "test_pipeline"
            assert result["data"]["dataSource"] == "s3://test-bucket/data.csv"
            assert result["data"]["targetTableOrProcedure"] == "test_table"
            assert result["data"]["autoStarted"] is True

            # Check that run_sql was called twice (CREATE and START)
            assert mock_run_sql_success.call_count == 2

            # Check the first call (CREATE PIPELINE)
            create_call = mock_run_sql_success.call_args_list[0]
            create_sql = create_call[1]["sql_query"]

            # Verify CREATE PIPELINE SQL contains expected elements
            assert "CREATE OR REPLACE PIPELINE test_pipeline AS" in create_sql
            assert "LOAD DATA S3://TEST-BUCKET/DATA.CSV" in create_sql
            assert "CREDENTIALS '{}'" in create_sql
            assert 'CONFIG \'{"region": "us-east-1"}\'' in create_sql
            assert "INTO test_table" in create_sql
            assert "FORMAT CSV" in create_sql
            assert "FIELDS TERMINATED BY ','" in create_sql

            # Check the second call (START PIPELINE)
            start_call = mock_run_sql_success.call_args_list[1]
            start_sql = start_call[1]["sql_query"]
            assert start_sql == "START PIPELINE IF NOT RUNNING test_pipeline;"


@pytest.mark.asyncio
async def test_create_pipeline_with_json_format():
    """Test create_pipeline with JSON format."""
    ctx = AsyncMock()
    ctx.info = AsyncMock()

    mock_run_sql_success = AsyncMock(return_value={"status": "success"})

    with patch("src.api.tools.database.database.run_sql", mock_run_sql_success):
        with patch("src.api.tools.database.database.config") as mock_config:
            mock_settings = MagicMock()
            mock_settings.analytics_manager.track_event = MagicMock()
            mock_config.get_settings.return_value = mock_settings
            mock_config.get_user_id.return_value = "test-user"

            result = await create_pipeline(
                ctx=ctx,
                pipeline_name="json_pipeline",
                data_source="s3://test-bucket/data.json",
                target_table_or_procedure="json_table",
                workspace_id="ws-12345678-1234-5678-1234-567812345678",
                file_format="JSON",
                auto_start=False,
            )

            assert result["status"] == "success"
            assert result["data"]["autoStarted"] is False

            # Check that run_sql was called only once (CREATE, no START)
            assert mock_run_sql_success.call_count == 1

            # Check the CREATE PIPELINE SQL
            create_call = mock_run_sql_success.call_args_list[0]
            create_sql = create_call[1]["sql_query"]

            assert "FORMAT JSON" in create_sql
            # JSON format should not have CSV-specific fields
            assert "FIELDS TERMINATED BY" not in create_sql


@pytest.mark.asyncio
async def test_create_pipeline_with_credentials():
    """Test create_pipeline passes username and password correctly."""
    ctx = AsyncMock()
    ctx.info = AsyncMock()

    mock_run_sql_success = AsyncMock(return_value={"status": "success"})

    with patch("src.api.tools.database.database.run_sql", mock_run_sql_success):
        with patch("src.api.tools.database.database.config") as mock_config:
            mock_settings = MagicMock()
            mock_settings.analytics_manager.track_event = MagicMock()
            mock_config.get_settings.return_value = mock_settings
            mock_config.get_user_id.return_value = "test-user"

            # Test with username and password
            result = await create_pipeline(
                ctx=ctx,
                pipeline_name="test_pipeline",
                data_source="s3://test-bucket/data.csv",
                target_table_or_procedure="test_table",
                workspace_id="ws-12345678-1234-5678-1234-567812345678",
                username="test_user",
                password="test_pass",
                auto_start=True,
            )

            assert result["status"] == "success"

            # Verify that both run_sql calls received username and password
            for call in mock_run_sql_success.call_args_list:
                assert call[1]["username"] == "test_user"
                assert call[1]["password"] == "test_pass"


@pytest.mark.asyncio
async def test_create_pipeline_error_handling():
    """Test create_pipeline handles errors properly."""
    ctx = AsyncMock()
    ctx.info = AsyncMock()

    # Mock run_sql to return an error
    mock_run_sql_error = AsyncMock(
        return_value={"status": "error", "message": "SQL execution failed"}
    )

    with patch("src.api.tools.database.database.run_sql", mock_run_sql_error):
        result = await create_pipeline(
            ctx=ctx,
            pipeline_name="error_pipeline",
            data_source="s3://test-bucket/data.csv",
            target_table_or_procedure="test_table",
            workspace_id="ws-12345678-1234-5678-1234-567812345678",
        )

        assert result["status"] == "error"
        assert "Failed to create pipeline" in result["message"]
        assert result["errorCode"] == "PIPELINE_CREATION_FAILED"


@pytest.mark.asyncio
async def test_create_pipeline_stage_data_source():
    """Test create_pipeline with Stage data source."""
    ctx = AsyncMock()
    ctx.info = AsyncMock()

    mock_run_sql_success = AsyncMock(return_value={"status": "success"})

    with patch("src.api.tools.database.database.run_sql", mock_run_sql_success):
        with patch("src.api.tools.database.database.config") as mock_config:
            mock_settings = MagicMock()
            mock_settings.analytics_manager.track_event = MagicMock()
            mock_config.get_settings.return_value = mock_settings
            mock_config.get_user_id.return_value = "test-user"

            result = await create_pipeline(
                ctx=ctx,
                pipeline_name="stage_pipeline",
                data_source="stage://my_data/file.csv",
                target_table_or_procedure="stage_table",
                workspace_id="ws-12345678-1234-5678-1234-567812345678",
            )

            assert result["status"] == "success"

            # Check the CREATE PIPELINE SQL contains proper Stage URL
            create_call = mock_run_sql_success.call_args_list[0]
            create_sql = create_call[1]["sql_query"]
            assert "LOAD DATA STAGE://MY_DATA/FILE.CSV" in create_sql
