"""Unit tests for Stage tools."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.api.tools.stage import (
    stage_list_files,
    stage_get_file,
    stage_create_folder,
    stage_upload_file_local,
    stage_upload_file_remote,
)
from src.api.tools.registery import register_tools
from src.config.config import RemoteSettings
from src.config.config import LocalSettings, _settings_ctx, _user_id_ctx
from src.analytics.manager import AnalyticsManager


@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment with mock settings and user ID."""
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


@pytest.fixture
def mock_ctx():
    """Create a mock MCP Context."""
    ctx = AsyncMock()
    ctx.info = AsyncMock()
    ctx.error = AsyncMock()
    return ctx


DEPLOYMENT_ID = "12345678-1234-1234-1234-123456789abc"


class TestPathNormalization:
    """Verify trailing-slash logic: folders get '/', files get it stripped."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "func,kwargs,expected_path_suffix",
        [
            (stage_list_files, {"path": "data"}, "data/"),
            (stage_list_files, {"path": "data/"}, "data/"),
            (stage_list_files, {"path": ""}, "/fs"),
            (
                stage_get_file,
                {"path": "file.csv/", "return_type": "metadata"},
                "file.csv",
            ),
            (stage_create_folder, {"path": "folder"}, "folder/"),
            (stage_create_folder, {"path": "folder/"}, "folder/"),
            (
                stage_upload_file_local,
                {"path": "dir/file.txt/", "content": "x"},
                "dir/file.txt",
            ),
            (
                stage_upload_file_remote,
                {"path": "dir/file.txt/", "content": "x"},
                "dir/file.txt",
            ),
        ],
    )
    async def test_path_normalization(
        self, mock_ctx, func, kwargs, expected_path_suffix
    ):
        with patch("src.api.tools.stage.stage.build_request") as mock_req:
            mock_req.return_value = {}
            await func(mock_ctx, DEPLOYMENT_ID, **kwargs)

        endpoint = mock_req.call_args.args[1]
        assert endpoint.endswith(expected_path_suffix)


class TestStageGetFile:
    """Test the branching logic in stage_get_file (3 return types + error paths)."""

    @pytest.mark.asyncio
    async def test_invalid_return_type(self, mock_ctx):
        result = await stage_get_file(
            mock_ctx, DEPLOYMENT_ID, "file.csv", return_type="invalid"
        )
        assert result["status"] == "error"
        assert result["errorCode"] == "INVALID_RETURN_TYPE"

    @pytest.mark.asyncio
    async def test_url_non_307_returns_error(self, mock_ctx):
        with patch("src.api.tools.stage.stage.build_request") as mock_req:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "unexpected"
            mock_req.return_value = mock_response

            result = await stage_get_file(
                mock_ctx, DEPLOYMENT_ID, "file.csv", return_type="url"
            )

        assert result["status"] == "error"
        assert result["errorCode"] == "UNEXPECTED_RESPONSE"

    @pytest.mark.asyncio
    async def test_content_non_200_returns_error(self, mock_ctx):
        with patch("src.api.tools.stage.stage.build_request") as mock_req:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.text = "not found"
            mock_req.return_value = mock_response

            result = await stage_get_file(
                mock_ctx, DEPLOYMENT_ID, "file.csv", return_type="content"
            )

        assert result["status"] == "error"
        assert result["errorCode"] == "CONTENT_FETCH_FAILED"

    @pytest.mark.asyncio
    async def test_content_returns_text(self, mock_ctx):
        with patch("src.api.tools.stage.stage.build_request") as mock_req:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "col1,col2\na,b\n"
            mock_req.return_value = mock_response

            result = await stage_get_file(
                mock_ctx, DEPLOYMENT_ID, "data/file.csv", return_type="content"
            )

        assert result["data"]["content"] == "col1,col2\na,b\n"


class TestStageUploadFileLocal:
    """Test input validation and file I/O in the local upload variant."""

    @pytest.mark.asyncio
    async def test_error_both_content_and_path(self, mock_ctx):
        result = await stage_upload_file_local(
            mock_ctx, DEPLOYMENT_ID, "f.txt", content="x", local_path="/some/path"
        )
        assert result["errorCode"] == "INVALID_ARGUMENTS"
        assert "not both" in result["message"]

    @pytest.mark.asyncio
    async def test_error_neither_content_nor_path(self, mock_ctx):
        result = await stage_upload_file_local(mock_ctx, DEPLOYMENT_ID, "f.txt")
        assert result["errorCode"] == "INVALID_ARGUMENTS"

    @pytest.mark.asyncio
    async def test_local_path_not_found(self, mock_ctx):
        result = await stage_upload_file_local(
            mock_ctx, DEPLOYMENT_ID, "f.txt", local_path="/nonexistent/file"
        )
        assert result["errorCode"] == "FILE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_reads_local_file_bytes(self, mock_ctx, tmp_path):
        local_file = tmp_path / "mcp_stage_test_data.bin"
        local_file.write_bytes(b"\x00\x01\x02")

        with patch("src.api.tools.stage.stage.build_request") as mock_req:
            mock_req.return_value = {}
            result = await stage_upload_file_local(
                mock_ctx,
                DEPLOYMENT_ID,
                "data/mcp_stage_test_data.bin",
                local_path=str(local_file),
            )

        assert result["status"] == "success"
        sent_bytes = mock_req.call_args.kwargs["files"]["file"][1]
        assert sent_bytes == b"\x00\x01\x02"

    @pytest.mark.asyncio
    async def test_extracts_filename_from_path(self, mock_ctx):
        with patch("src.api.tools.stage.stage.build_request") as mock_req:
            mock_req.return_value = {}
            result = await stage_upload_file_local(
                mock_ctx, DEPLOYMENT_ID, "deep/nested/report.csv", content="a,b"
            )

        assert result["data"]["filename"] == "report.csv"


class TestToolRegistration:
    """Verify register_tools registers the correct upload variant per mode."""

    def _get_upload_params(self, settings):
        _settings_ctx.set(settings)
        mcp = MagicMock()
        register_tools(mcp)
        for tool_call, decorator_call in zip(
            mcp.tool.call_args_list,
            mcp.tool.return_value.call_args_list,
        ):
            if tool_call.kwargs["name"] == "stage_upload_file":
                func = decorator_call.args[0]
                import inspect

                return list(inspect.signature(func).parameters.keys())
        return None

    def test_local_mode_has_local_path_param(self, setup_test_env):
        params = self._get_upload_params(setup_test_env)
        assert "local_path" in params

    def test_remote_mode_has_no_local_path_param(self):
        settings = RemoteSettings.model_construct()
        params = self._get_upload_params(settings)
        assert "local_path" not in params


class TestErrorHandling:
    """Spot-check that API errors are caught and wrapped (one example suffices)."""

    @pytest.mark.asyncio
    async def test_api_error_returns_error_dict(self, mock_ctx):
        with patch("src.api.tools.stage.stage.build_request") as mock_req:
            mock_req.side_effect = Exception("connection refused")
            result = await stage_list_files(mock_ctx, DEPLOYMENT_ID)

        assert result["status"] == "error"
        assert "connection refused" in result["message"]
