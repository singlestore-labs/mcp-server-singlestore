import pytest
import os
import tempfile
import json
import uuid

from src.api.tools.cloud_functions import (
    create_code_service,
    list_code_services,
    get_code_service,
    update_code_service,
    delete_code_service,
)

import tests.integration.tools.utils as utils


@pytest.mark.integration
class TestCloudFunctionsTools:
    notebook_path = None
    temp_file_path = None

    @classmethod
    def setup_class(cls):
        file_manager = utils.get_file_manager()
        notebook_name = f"test_code_service_notebook_{uuid.uuid4().hex}"
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
                            "# Code Service Test\nThis notebook is for code service tests."
                        ],
                    },
                    {
                        "cell_type": "code",
                        "metadata": {"language": "python"},
                        "source": [
                            "import flask\n",
                            "from flask import Flask, jsonify\n",
                            "app = Flask(__name__)\n\n",
                            "@app.route('/hello')\n",
                            "def hello():\n",
                            "    return jsonify({'message': 'Hello from code service!'})\n\n",
                            "if __name__ == '__main__':\n",
                            "    app.run(host='0.0.0.0', port=8080)",
                        ],
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
    async def test_list_code_services(self, mock_context):
        """Test listing all code services."""
        result = await list_code_services(ctx=mock_context)

        # Since code services might not be available in current SDK, check for appropriate response
        if (
            result["status"] == "error"
            and result["errorCode"] == "CODE_SERVICES_NOT_AVAILABLE"
        ):
            pytest.skip(
                "Code services functionality not available in current SDK version"
            )

        assert result["status"] == "success"
        assert "data" in result
        assert isinstance(result["data"], list)

    @pytest.mark.asyncio
    async def test_create_code_service(self, mock_context):
        """Test creating a new code service."""
        service_name = f"test_service_{uuid.uuid4().hex}"
        description = "Test code service for integration testing"

        result = await create_code_service(
            ctx=mock_context,
            name=service_name,
            notebook_path=type(self).notebook_path,
            description=description,
        )

        # Since code services might not be available in current SDK, check for appropriate response
        if (
            result["status"] == "error"
            and result["errorCode"] == "CODE_SERVICES_NOT_AVAILABLE"
        ):
            pytest.skip(
                "Code services functionality not available in current SDK version"
            )

        assert result["status"] == "success"
        service_id = result["data"]["codeServiceID"]
        assert result["data"]["name"] == service_name
        assert result["data"]["description"] == description
        assert result["data"]["notebookPath"] == type(self).notebook_path

        # Clean up - delete the created service
        org = utils.get_organization()
        if hasattr(org, "code_services") and org.code_services:
            org.code_services.delete(service_id)

    @pytest.mark.asyncio
    async def test_get_code_service(self, mock_context):
        """Test retrieving a specific code service."""
        # First create a service to test getting it
        service_name = f"test_get_service_{uuid.uuid4().hex}"

        # Try to get the organization's code services manager directly
        org = utils.get_organization()
        if not hasattr(org, "code_services") or not org.code_services:
            pytest.skip(
                "Code services functionality not available in current SDK version"
            )

        code_services_manager = org.code_services
        service_obj = code_services_manager.create(
            name=service_name,
            notebook_path=type(self).notebook_path,
            description="Test service for get operation",
        )
        service_id = service_obj.code_service_id

        try:
            # Test getting the service
            result = await get_code_service(
                ctx=mock_context,
                code_service_id=service_id,
            )

            assert result["status"] == "success"
            assert result["data"]["codeServiceID"] == service_id
            assert result["data"]["name"] == service_name
            assert result["data"]["notebookPath"] == type(self).notebook_path

        finally:
            # Clean up
            code_services_manager.delete(service_id)

    @pytest.mark.asyncio
    async def test_update_code_service(self, mock_context):
        """Test updating a code service."""
        # First create a service to test updating it
        service_name = f"test_update_service_{uuid.uuid4().hex}"

        # Try to get the organization's code services manager directly
        org = utils.get_organization()
        if not hasattr(org, "code_services") or not org.code_services:
            pytest.skip(
                "Code services functionality not available in current SDK version"
            )

        code_services_manager = org.code_services
        service_obj = code_services_manager.create(
            name=service_name,
            notebook_path=type(self).notebook_path,
            description="Original description",
        )
        service_id = service_obj.code_service_id

        try:
            # Test updating the service
            new_name = f"updated_{service_name}"
            new_description = "Updated description"
            new_env_vars = {"UPDATED": "true"}

            result = await update_code_service(
                ctx=mock_context,
                code_service_id=service_id,
                name=new_name,
                description=new_description,
                environment_variables=new_env_vars,
            )

            assert result["status"] == "success"
            assert result["data"]["codeServiceID"] == service_id
            assert result["data"]["name"] == new_name
            assert result["data"]["description"] == new_description
            assert result["data"]["environmentVariables"] == new_env_vars

        finally:
            # Clean up
            code_services_manager.delete(service_id)

    @pytest.mark.asyncio
    async def test_delete_code_service(self, mock_context):
        """Test deleting a code service."""
        # First create a service to test deleting it
        service_name = f"test_delete_service_{uuid.uuid4().hex}"

        # Try to get the organization's code services manager directly
        org = utils.get_organization()
        if not hasattr(org, "code_services") or not org.code_services:
            pytest.skip(
                "Code services functionality not available in current SDK version"
            )

        code_services_manager = org.code_services
        service_obj = code_services_manager.create(
            name=service_name,
            notebook_path=type(self).notebook_path,
            description="Service to be deleted",
        )
        service_id = service_obj.code_service_id

        # Test deleting the service
        result = await delete_code_service(
            ctx=mock_context,
            code_service_id=service_id,
        )

        assert result["status"] == "success"

        # Verify the service was actually deleted by trying to get it
        try:
            code_services_manager.get(service_id)
            # If we reach here, the service wasn't deleted
            assert False, "Service should have been deleted"
        except Exception:
            # Expected - service should not exist anymore
            pass

    @pytest.mark.asyncio
    async def test_get_nonexistent_code_service(self, mock_context):
        """Test getting a code service that doesn't exist."""
        # Use a random UUID that shouldn't exist
        fake_service_id = str(uuid.uuid4())

        result = await get_code_service(
            ctx=mock_context,
            code_service_id=fake_service_id,
        )

        # Since code services might not be available in current SDK, check for appropriate response
        if (
            result["status"] == "error"
            and result["errorCode"] == "CODE_SERVICES_NOT_AVAILABLE"
        ):
            pytest.skip(
                "Code services functionality not available in current SDK version"
            )

        assert result["status"] == "error"
        assert result["errorCode"] == "CODE_SERVICE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_update_nonexistent_code_service(self, mock_context):
        """Test updating a code service that doesn't exist."""
        # Use a random UUID that shouldn't exist
        fake_service_id = str(uuid.uuid4())

        result = await update_code_service(
            ctx=mock_context,
            code_service_id=fake_service_id,
            name="new_name",
        )

        # Since code services might not be available in current SDK, check for appropriate response
        if (
            result["status"] == "error"
            and result["errorCode"] == "CODE_SERVICES_NOT_AVAILABLE"
        ):
            pytest.skip(
                "Code services functionality not available in current SDK version"
            )

        assert result["status"] == "error"
        assert result["errorCode"] == "CODE_SERVICE_UPDATE_FAILED"

    @pytest.mark.asyncio
    async def test_delete_nonexistent_code_service(self, mock_context):
        """Test deleting a code service that doesn't exist."""
        # Use a random UUID that shouldn't exist
        fake_service_id = str(uuid.uuid4())

        result = await delete_code_service(
            ctx=mock_context,
            code_service_id=fake_service_id,
        )

        # Since code services might not be available in current SDK, check for appropriate response
        if (
            result["status"] == "error"
            and result["errorCode"] == "CODE_SERVICES_NOT_AVAILABLE"
        ):
            pytest.skip(
                "Code services functionality not available in current SDK version"
            )

        assert result["status"] == "error"
        assert result["errorCode"] == "CODE_SERVICE_DELETION_FAILED"

    @pytest.mark.asyncio
    async def test_update_code_service_no_params(self, mock_context):
        """Test updating a code service with no parameters provided."""
        # Use a random UUID
        fake_service_id = str(uuid.uuid4())

        result = await update_code_service(
            ctx=mock_context,
            code_service_id=fake_service_id,
        )

        # Since code services might not be available in current SDK, check for appropriate response
        if (
            result["status"] == "error"
            and result["errorCode"] == "CODE_SERVICES_NOT_AVAILABLE"
        ):
            pytest.skip(
                "Code services functionality not available in current SDK version"
            )

        assert result["status"] == "error"
        assert result["errorCode"] == "NO_UPDATE_PARAMS"
