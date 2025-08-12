import pytest
import os
import tempfile
import json
import uuid

from src.api.tools.jobs import (
    create_job_from_notebook,
    get_job,
    delete_job,
)

import tests.integration.tools.utils as utils


@pytest.mark.integration
class TestJobsTools:
    notebook_path = None
    temp_file_path = None

    @classmethod
    def setup_class(cls):
        file_manager = utils.get_file_manager()
        notebook_name = f"test_job_notebook_{uuid.uuid4().hex}"
        cls.notebook_path = f"{notebook_name}.ipynb"
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
        cls.temp_file_path = temp_file.name
        temp_file.close()
        file_manager.shared_space.upload_file(
            local_path=cls.temp_file_path, path=cls.notebook_path
        )
        assert file_manager.shared_space.exists(cls.notebook_path)

    @classmethod
    def teardown_class(cls):
        file_manager = utils.get_file_manager()
        if cls.notebook_path and file_manager.shared_space.exists(cls.notebook_path):
            file_manager.shared_space.remove(cls.notebook_path)
        if cls.temp_file_path and os.path.exists(cls.temp_file_path):
            os.remove(cls.temp_file_path)

    @pytest.mark.asyncio
    async def test_create_one_time_job_from_notebook(self, mock_context):
        job_name = f"test_job_{uuid.uuid4().hex}"
        mode = "Once"
        result = await create_job_from_notebook(
            ctx=mock_context,
            name=job_name,
            notebook_path=type(self).notebook_path,
            mode=mode,
        )
        assert result["status"] == "success"
        job_id = result["data"]["jobID"]
        assert result["data"]["name"] == job_name
        assert result["data"]["schedule"]["mode"] == "Once"
        org = utils.get_organization()
        jobs_manager = org.jobs
        deleted = jobs_manager.delete(job_id)
        assert deleted is True

    @pytest.mark.asyncio
    async def test_create_recurrent_job_from_notebook(self, mock_context):
        job_name = f"test_recurrent_job_{uuid.uuid4().hex}"
        mode = "Recurring"
        execution_interval_in_minutes = 30
        result = await create_job_from_notebook(
            ctx=mock_context,
            name=job_name,
            notebook_path=type(self).notebook_path,
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
        org = utils.get_organization()
        jobs_manager = org.jobs
        deleted = jobs_manager.delete(job_id)
        assert deleted is True

    @pytest.mark.asyncio
    async def test_get_job_tool(self, mock_context):
        job_name = f"test_get_job_{uuid.uuid4().hex}"
        org = utils.get_organization()
        jobs_manager = org.jobs
        job_obj = jobs_manager.schedule(
            notebook_path=type(self).notebook_path,
            name=job_name,
            mode=jobs_manager.modes().ONCE,
            create_snapshot=True,
        )
        job_id = job_obj.job_id
        job_info = await get_job(
            ctx=mock_context,
            job_id=job_id,
        )
        assert job_info["status"] == "success"
        assert job_info["data"]["jobID"] == job_id
        assert job_info["data"]["name"] == job_name
        assert job_info["data"]["schedule"]["mode"] == "Once"
        deleted = jobs_manager.delete(job_id)
        assert deleted is True

    @pytest.mark.asyncio
    async def test_delete_job_tool(self, mock_context):
        job_name = f"test_delete_job_{uuid.uuid4().hex}"
        org = utils.get_organization()
        jobs_manager = org.jobs
        job_obj = jobs_manager.schedule(
            notebook_path=type(self).notebook_path,
            name=job_name,
            mode=jobs_manager.modes().ONCE,
            create_snapshot=True,
        )
        job_id = job_obj.job_id
        delete_result = await delete_job(
            ctx=mock_context,
            job_id=job_id,
        )
        assert delete_result["status"] == "success"
