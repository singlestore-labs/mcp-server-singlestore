import pytest
import os

from src.api.tools.notebooks.notebooks import (
    create_notebook_file,
    upload_notebook_file,
)

import tests.integration.tools.utils as utils


def sample_notebook_content():
    return {
        "cells": [
            {"type": "markdown", "content": "# Test Notebook\nThis is a test."},
            {"type": "code", "content": "print('Hello, world!')"},
        ]
    }


@pytest.mark.integration
class TestNotebookTools:
    @pytest.mark.asyncio
    async def test_create_notebook_file(self, mock_context):
        content = sample_notebook_content()
        result = await create_notebook_file(ctx=mock_context, content=content)
        assert result["status"] == "success"
        temp_file_path = result["data"]["tempFilePath"]
        assert os.path.exists(temp_file_path)
        os.remove(temp_file_path)

    @pytest.mark.asyncio
    async def test_upload_notebook_file(self, mock_context):
        import uuid

        content = sample_notebook_content()
        temp_result = await create_notebook_file(ctx=mock_context, content=content)
        temp_file_path = temp_result["data"]["tempFilePath"]
        upload_name = f"test_upload_notebook_{uuid.uuid4().hex}"

        # Upload to shared space
        upload_result_shared = await upload_notebook_file(
            ctx=mock_context,
            local_path=temp_file_path,
            upload_name=upload_name,
            upload_location="shared",
        )
        assert upload_result_shared["status"] == "success"

        # Upload to personal space
        upload_result_personal = await upload_notebook_file(
            ctx=mock_context,
            local_path=temp_file_path,
            upload_name=upload_name,
            upload_location="personal",
        )
        assert upload_result_personal["status"] == "success"

        os.remove(temp_file_path)

        # Use s2 package to delete the uploaded notebooks
        file_manager = utils.get_file_manager()
        file_manager.shared_space.remove(f"{upload_name}.ipynb")
        file_manager.personal_space.remove(f"{upload_name}.ipynb")
