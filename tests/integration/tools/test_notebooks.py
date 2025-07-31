import pytest
import os
import tempfile
import json
import uuid

from src.api.tools.notebooks.notebooks import (
    create_notebook_file,
    upload_notebook_file,
    create_job_from_notebook,
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

    @pytest.mark.asyncio
    async def test_create_one_time_job_from_notebook(self, mock_context):
        file_manager = utils.get_file_manager()

        # Create notebook content
        notebook_name = f"test_job_notebook_{uuid.uuid4().hex}"
        notebook_path = f"{notebook_name}.ipynb"

        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".ipynb", delete=False)
        json.dump(
            {
                "nbformat": 4,
                "nbformat_minor": 5,
                "cells": [
                    {
                        "cell_type": "markdown",
                        "metadata": {"language": "markdown"},
                        "source": [
                            "# Job Test\nThis notebook is for job scheduling tests."
                        ],
                    },
                    {
                        "cell_type": "code",
                        "metadata": {"language": "python"},
                        "source": ["print('Job test')"],
                    },
                ],
            },
            temp_file,
            indent=2,
        )
        temp_file_path = temp_file.name
        temp_file.close()

        # Upload notebook to shared space
        file_manager.shared_space.upload_file(
            local_path=temp_file_path, path=notebook_path
        )
        assert file_manager.shared_space.exists(notebook_path)

        # Create job
        job_name = f"test_job_{uuid.uuid4().hex}"
        mode = "Once"

        result = await create_job_from_notebook(
            ctx=mock_context,
            name=job_name,
            notebook_path=notebook_path,
            mode=mode,
        )

        assert result["status"] == "success"
        job_id = result["data"]["jobID"]
        assert result["data"]["name"] == job_name
        assert result["data"]["schedule"]["mode"] == "Once"

        # Remove job using job manager from organization
        org = utils.get_organization()
        jobs_manager = org.jobs
        deleted = jobs_manager.delete(job_id)
        assert deleted is True

        # Remove notebook and job
        file_manager.shared_space.remove(notebook_path)
        os.remove(temp_file_path)

    @pytest.mark.asyncio
    async def test_create_recurrent_job_from_notebook(self, mock_context):
        file_manager = utils.get_file_manager()

        # Create notebook content
        notebook_name = f"test_recurrent_job_notebook_{uuid.uuid4().hex}"
        notebook_path = f"{notebook_name}.ipynb"

        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".ipynb", delete=False)
        json.dump(
            {
                "nbformat": 4,
                "nbformat_minor": 5,
                "cells": [
                    {
                        "cell_type": "markdown",
                        "metadata": {"language": "markdown"},
                        "source": [
                            "# Recurrent Job Test\nThis notebook is for recurrent job scheduling tests."
                        ],
                    },
                    {
                        "cell_type": "code",
                        "metadata": {"language": "python"},
                        "source": ["print('Recurrent job test')"],
                    },
                ],
            },
            temp_file,
            indent=2,
        )
        temp_file_path = temp_file.name
        temp_file.close()

        # Upload notebook to shared space
        file_manager.shared_space.upload_file(
            local_path=temp_file_path, path=notebook_path
        )
        assert file_manager.shared_space.exists(notebook_path)

        # Create job
        job_name = f"test_recurrent_job_{uuid.uuid4().hex}"
        mode = "Recurring"
        execution_interval_in_minutes = 30

        result = await create_job_from_notebook(
            ctx=mock_context,
            name=job_name,
            notebook_path=notebook_path,
            mode=mode,
            execution_interval_in_minutes=execution_interval_in_minutes,
        )

        assert result["status"] == "success"
        job_id = result["data"]["jobID"]
        assert result["data"]["name"] == job_name
        assert result["data"]["schedule"]["mode"] == "Recurring"
        assert (
            result["data"]["schedule"]["executionIntervalInMinutes"]
            == execution_interval_in_minutes
        )

        # Remove job using job manager from organization
        org = utils.get_organization()
        jobs_manager = org.jobs
        deleted = jobs_manager.delete(job_id)
        assert deleted is True

        # Remove notebook and job
        file_manager.shared_space.remove(notebook_path)
        os.remove(temp_file_path)
