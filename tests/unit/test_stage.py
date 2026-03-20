"""Unit tests for Stage tools."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.api.tools.stage import (
    stage_list_files,
    stage_get_file,
    stage_create_folder,
    stage_upload_file_local,
    stage_upload_file_remote,
    stage_move,
    stage_delete,
)
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


class TestStageListFiles:
    @pytest.mark.asyncio
    async def test_list_root(self, mock_ctx):
        with patch("src.api.tools.stage.stage.build_request") as mock_req:
            mock_req.return_value = [{"name": "file.csv", "type": "file"}]
            result = await stage_list_files(mock_ctx, DEPLOYMENT_ID)

        assert result["status"] == "success"
        assert result["data"] == [{"name": "file.csv", "type": "file"}]
        mock_req.assert_called_once_with("GET", f"stage/{DEPLOYMENT_ID}/fs")


class TestStageGetFile:
    @pytest.mark.asyncio
    async def test_get_metadata(self, mock_ctx):
        with patch("src.api.tools.stage.stage.build_request") as mock_req:
            mock_req.return_value = {"size": 1024, "type": "text/csv"}
            result = await stage_get_file(
                mock_ctx, DEPLOYMENT_ID, "data/file.csv", return_type="metadata"
            )

        assert result["status"] == "success"
        assert result["data"] == {"size": 1024, "type": "text/csv"}
        mock_req.assert_called_once_with(
            "GET",
            f"stage/{DEPLOYMENT_ID}/fs/data/file.csv",
            params={"metadata": "true"},
        )

    @pytest.mark.asyncio
    async def test_get_url(self, mock_ctx):
        with patch("src.api.tools.stage.stage.build_request") as mock_req:
            mock_response = MagicMock()
            mock_response.status_code = 307
            mock_response.headers = {"Location": "https://download.example.com/file"}
            mock_req.return_value = mock_response

            result = await stage_get_file(
                mock_ctx, DEPLOYMENT_ID, "data/file.csv", return_type="url"
            )

        assert result["status"] == "success"
        assert result["data"]["url"] == "https://download.example.com/file"
        mock_req.assert_called_once_with(
            "GET",
            f"stage/{DEPLOYMENT_ID}/fs/data/file.csv",
            raw_response=True,
            allow_redirects=False,
        )

    @pytest.mark.asyncio
    async def test_get_content(self, mock_ctx):
        with patch("src.api.tools.stage.stage.build_request") as mock_req:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "col1,col2\na,b\n"
            mock_req.return_value = mock_response

            result = await stage_get_file(
                mock_ctx, DEPLOYMENT_ID, "data/file.csv", return_type="content"
            )

        assert result["status"] == "success"
        assert result["data"]["content"] == "col1,col2\na,b\n"
        mock_req.assert_called_once_with(
            "GET",
            f"stage/{DEPLOYMENT_ID}/fs/data/file.csv",
            raw_response=True,
        )

    @pytest.mark.asyncio
    async def test_invalid_return_type(self, mock_ctx):
        result = await stage_get_file(
            mock_ctx, DEPLOYMENT_ID, "file.csv", return_type="invalid"
        )
        assert result["status"] == "error"
        assert result["errorCode"] == "INVALID_RETURN_TYPE"


class TestStageCreateFolder:
    @pytest.mark.asyncio
    async def test_create_folder(self, mock_ctx):
        with patch("src.api.tools.stage.stage.build_request") as mock_req:
            mock_req.return_value = {}
            result = await stage_create_folder(mock_ctx, DEPLOYMENT_ID, "new_folder")

        assert result["status"] == "success"
        mock_req.assert_called_once_with(
            "PUT", f"stage/{DEPLOYMENT_ID}/fs/new_folder/", data=None
        )


class TestStageUploadFile:
    @pytest.mark.asyncio
    async def test_upload_with_content(self, mock_ctx):
        with patch("src.api.tools.stage.stage.build_request") as mock_req:
            mock_req.return_value = {}
            result = await stage_upload_file_local(
                mock_ctx, DEPLOYMENT_ID, "data/test.csv", content="a,b\n1,2\n"
            )

        assert result["status"] == "success"
        assert result["data"]["filename"] == "test.csv"
        call_kwargs = mock_req.call_args
        assert call_kwargs.kwargs["files"]["file"][0] == "test.csv"
        assert call_kwargs.kwargs["files"]["file"][1] == b"a,b\n1,2\n"

    @pytest.mark.asyncio
    async def test_upload_with_local_path(self, mock_ctx, tmp_path):
        local_file = tmp_path / "data.bin"
        local_file.write_bytes(b"\x00\x01\x02\x03")

        with patch("src.api.tools.stage.stage.build_request") as mock_req:
            mock_req.return_value = {}
            result = await stage_upload_file_local(
                mock_ctx, DEPLOYMENT_ID, "data/data.bin", local_path=str(local_file)
            )

        assert result["status"] == "success"
        assert result["data"]["filename"] == "data.bin"
        call_kwargs = mock_req.call_args
        assert call_kwargs.kwargs["files"]["file"][1] == b"\x00\x01\x02\x03"

    @pytest.mark.asyncio
    async def test_upload_error_both_provided(self, mock_ctx):
        result = await stage_upload_file_local(
            mock_ctx,
            DEPLOYMENT_ID,
            "file.txt",
            content="text",
            local_path="/some/path",
        )
        assert result["status"] == "error"
        assert result["errorCode"] == "INVALID_ARGUMENTS"
        assert "not both" in result["message"]

    @pytest.mark.asyncio
    async def test_upload_error_neither_provided(self, mock_ctx):
        result = await stage_upload_file_local(mock_ctx, DEPLOYMENT_ID, "file.txt")
        assert result["status"] == "error"
        assert result["errorCode"] == "INVALID_ARGUMENTS"

    @pytest.mark.asyncio
    async def test_upload_local_path_not_found(self, mock_ctx):
        result = await stage_upload_file_local(
            mock_ctx,
            DEPLOYMENT_ID,
            "file.txt",
            local_path="/nonexistent/path/file.txt",
        )
        assert result["status"] == "error"
        assert result["errorCode"] == "FILE_NOT_FOUND"


class TestStageMove:
    @pytest.mark.asyncio
    async def test_move_file(self, mock_ctx):
        with patch("src.api.tools.stage.stage.build_request") as mock_req:
            mock_req.return_value = {}
            result = await stage_move(
                mock_ctx, DEPLOYMENT_ID, "old/file.csv", "new/file.csv"
            )

        assert result["status"] == "success"
        mock_req.assert_called_once_with(
            "PATCH",
            f"stage/{DEPLOYMENT_ID}/fs/old/file.csv",
            data={"newPath": "new/file.csv"},
        )


class TestStageDelete:
    @pytest.mark.asyncio
    async def test_delete_file(self, mock_ctx):
        with patch("src.api.tools.stage.stage.build_request") as mock_req:
            mock_req.return_value = {}
            result = await stage_delete(mock_ctx, DEPLOYMENT_ID, "old_file.csv")

        assert result["status"] == "success"
        mock_req.assert_called_once_with(
            "DELETE", f"stage/{DEPLOYMENT_ID}/fs/old_file.csv"
        )

    @pytest.mark.asyncio
    async def test_delete_folder(self, mock_ctx):
        with patch("src.api.tools.stage.stage.build_request") as mock_req:
            mock_req.return_value = {}
            result = await stage_delete(mock_ctx, DEPLOYMENT_ID, "folder/")

        assert result["status"] == "success"
        mock_req.assert_called_once_with("DELETE", f"stage/{DEPLOYMENT_ID}/fs/folder/")


class TestPathNormalization:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "func,kwargs,expected_path_suffix",
        [
            (stage_list_files, {"path": "data"}, "data/"),
            (stage_list_files, {"path": "data/"}, "data/"),
            (stage_get_file, {"path": "file.csv/", "return_type": "metadata"}, "file.csv"),
            (stage_create_folder, {"path": "folder"}, "folder/"),
            (stage_create_folder, {"path": "folder/"}, "folder/"),
            (stage_upload_file_local, {"path": "file.txt/", "content": "x"}, "file.txt"),
            (stage_upload_file_remote, {"path": "file.txt/", "content": "x"}, "file.txt"),
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


class TestErrorHandling:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "func,kwargs",
        [
            (stage_list_files, {}),
            (stage_get_file, {"path": "file.csv", "return_type": "metadata"}),
            (stage_create_folder, {"path": "folder"}),
            (stage_upload_file_local, {"path": "file.txt", "content": "x"}),
            (stage_upload_file_remote, {"path": "file.txt", "content": "x"}),
            (stage_move, {"source_path": "a.csv", "destination_path": "b.csv"}),
            (stage_delete, {"path": "file.csv"}),
        ],
    )
    async def test_error_handling(self, mock_ctx, func, kwargs):
        with patch("src.api.tools.stage.stage.build_request") as mock_req:
            mock_req.side_effect = Exception("API error")
            result = await func(mock_ctx, DEPLOYMENT_ID, **kwargs)

        assert result["status"] == "error"
        assert "API error" in result["message"]
