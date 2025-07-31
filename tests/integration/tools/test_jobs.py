import pytest
import os
import tempfile
import json
import uuid

from src.api.tools.jobs import (
    create_job_from_notebook,
)

import tests.integration.tools.utils as utils


@pytest.mark.integration
class TestJobsTools:
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
