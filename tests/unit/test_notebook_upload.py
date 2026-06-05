import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.tools.notebooks import utils
from src.api.tools.notebooks.notebooks import upload_notebook_file


@pytest.fixture
def ctx():
    return AsyncMock()


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.s2_api_base_url = "https://api.singlestore.com"
    settings.analytics_manager = MagicMock()
    settings.analytics_manager.track_event = MagicMock()
    return settings


def _write_notebook(path, content):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(content, f)


@pytest.mark.asyncio
async def test_upload_normalizes_missing_language_before_upload(
    ctx, tmp_path, mock_settings
):
    notebook_path = tmp_path / "missing_language.ipynb"
    _write_notebook(
        notebook_path,
        {"cells": [{"type": "code", "content": "print(1)"}]},
    )

    captured = {}
    real_validate = utils.validate_notebook_schema

    def validate_and_capture(content):
        captured["notebook"] = content
        return real_validate(content)

    mock_file_info = MagicMock(path="shared/test.ipynb", type="file", format="ipynb")

    def capture_upload(local_path, path):
        with open(local_path, encoding="utf-8") as f:
            captured["uploaded"] = json.load(f)
        return mock_file_info

    mock_space = MagicMock()
    mock_space.upload_file.side_effect = capture_upload
    mock_fm = MagicMock()
    mock_fm.shared_space = mock_space

    with (
        patch(
            "src.api.tools.notebooks.notebooks.config.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.api.tools.notebooks.notebooks.config.get_user_id",
            return_value="test-user",
        ),
        patch("src.api.tools.notebooks.notebooks.get_org_id", return_value=None),
        patch(
            "src.api.tools.notebooks.notebooks.get_access_token",
            return_value="mock-token",
        ),
        patch(
            "src.api.tools.notebooks.notebooks.utils.check_if_file_exists",
            return_value=False,
        ),
        patch(
            "src.api.tools.notebooks.notebooks.utils.validate_notebook_schema",
            side_effect=validate_and_capture,
        ),
        patch(
            "src.api.tools.notebooks.notebooks.s2.manage_files",
            return_value=mock_fm,
        ),
        patch(
            "src.api.tools.notebooks.notebooks.call_sdk_with_retry",
            side_effect=lambda fn: fn(),
        ),
    ):
        result = await upload_notebook_file(
            ctx=ctx,
            local_path=str(notebook_path),
            upload_name="test-notebook",
            upload_location="shared",
        )

    assert result["status"] == "success"
    assert captured["notebook"]["cells"][0]["metadata"]["language"] == "python"
    assert captured["uploaded"]["cells"][0]["metadata"]["language"] == "python"
    assert result["data"]["schemaValidated"] is True


@pytest.mark.asyncio
async def test_upload_fails_on_unsupported_language(ctx, tmp_path, mock_settings):
    notebook_path = tmp_path / "unsupported_language.ipynb"
    _write_notebook(
        notebook_path,
        {
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["puts 'hi'"],
                    "metadata": {"language": "ruby"},
                    "outputs": [],
                    "execution_count": None,
                }
            ]
        },
    )

    with (
        patch(
            "src.api.tools.notebooks.notebooks.config.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.api.tools.notebooks.notebooks.call_sdk_with_retry",
        ) as mock_upload,
    ):
        result = await upload_notebook_file(
            ctx=ctx,
            local_path=str(notebook_path),
            upload_name="bad-language-notebook",
            upload_location="shared",
        )

    assert result["status"] == "error"
    assert result["errorCode"] == "INVALID_CELL_LANGUAGE"
    mock_upload.assert_not_called()


@pytest.mark.asyncio
async def test_upload_fails_when_normalization_still_invalid_schema(
    ctx, tmp_path, mock_settings
):
    notebook_path = tmp_path / "invalid_nbformat.ipynb"
    _write_notebook(
        notebook_path,
        {"nbformat": 99, "nbformat_minor": 5, "metadata": {}, "cells": []},
    )

    with (
        patch(
            "src.api.tools.notebooks.notebooks.config.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.api.tools.notebooks.notebooks.call_sdk_with_retry",
        ) as mock_upload,
    ):
        result = await upload_notebook_file(
            ctx=ctx,
            local_path=str(notebook_path),
            upload_name="invalid-notebook",
            upload_location="shared",
        )

    assert result["status"] == "error"
    assert result["errorCode"] == "SCHEMA_VALIDATION_FAILED"
    mock_upload.assert_not_called()
