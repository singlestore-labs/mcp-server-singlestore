import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.tools.cloud_functions import (
    create_cloud_function,
    update_cloud_function,
)
from src.config.config import LocalSettings, _settings_ctx, _user_id_ctx
from src.analytics.manager import AnalyticsManager


@pytest.fixture(autouse=True)
def setup_test_env():
    settings = LocalSettings(
        api_key="mock_api_key_12345",
        transport="stdio",
        is_remote=False,
        s2_api_base_url="https://api.singlestore.com",
        graphql_public_endpoint="https://backend.singlestore.com/public",
    )
    settings.analytics_manager = MagicMock(spec=AnalyticsManager)
    settings.analytics_manager.track_event = MagicMock()

    _settings_ctx.set(settings)
    _user_id_ctx.set("test-user-12345")
    try:
        yield settings
    finally:
        _settings_ctx.set(None)
        _user_id_ctx.set(None)


class TestCloudFunctionsValidation:
    @pytest.fixture
    def ctx(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_create_cloud_function_invalid_target_type(self, ctx):
        result = await create_cloud_function(
            ctx=ctx,
            name="test-fn",
            notebook_path="shared/test.ipynb",
            target_id="00000000-0000-0000-0000-000000000000",
            target_type="INVALID",
        )
        assert result["status"] == "error"
        assert result["errorCode"] == "INVALID_TARGET_TYPE"

    @pytest.mark.asyncio
    async def test_create_cloud_function_virtual_workspace_without_database_name(
        self, ctx
    ):
        result = await create_cloud_function(
            ctx=ctx,
            name="test-fn",
            notebook_path="shared/test.ipynb",
            target_id="00000000-0000-0000-0000-000000000000",
            target_type="VirtualWorkspace",
        )
        assert result["status"] == "error"
        assert result["errorCode"] == "MISSING_DATABASE_NAME"

    @pytest.mark.asyncio
    async def test_update_cloud_function_no_fields(self, ctx):
        result = await update_cloud_function(
            ctx=ctx,
            cloud_function_id="00000000-0000-0000-0000-000000000000",
        )
        assert result["status"] == "error"
        assert result["errorCode"] == "NO_FIELDS_TO_UPDATE"

    @pytest.mark.asyncio
    async def test_update_cloud_function_snapshot_only(self, ctx):
        with patch(
            "src.api.tools.cloud_functions.cloud_functions.build_request"
        ) as mock_req:
            mock_req.return_value = {
                "serviceID": "00000000-0000-0000-0000-000000000000"
            }
            result = await update_cloud_function(
                ctx=ctx,
                cloud_function_id="00000000-0000-0000-0000-000000000000",
                update_notebook_snapshot=True,
            )

        assert result["status"] == "success"
        mock_req.assert_called_once()
        assert mock_req.call_args.kwargs["params"]["updateNotebookSnapshot"] == "true"

    @pytest.mark.asyncio
    async def test_update_cloud_function_invalid_target_type(self, ctx):
        result = await update_cloud_function(
            ctx=ctx,
            cloud_function_id="00000000-0000-0000-0000-000000000000",
            target_type="BADTYPE",
        )
        assert result["status"] == "error"
        assert result["errorCode"] == "INVALID_TARGET_TYPE"
