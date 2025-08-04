import pytest
import random
import secrets
import re


import src.api.tools.workspaces.utils as workspace_utils
from src.api.tools.workspaces import (
    workspace_groups_info,
    workspaces_info,
    resume_workspace,
)


def clean_name(s):
    return re.sub(r"[^\w]", r"-", s).replace("_", "-").lower()


@pytest.mark.integration
class TestWorkspaceGroupAndWorkspaceTools:
    """Integration test for listing workspace groups and workspaces."""

    manager = None
    workspace_group = None
    workspace = None
    password = None

    @classmethod
    def setup_class(cls):
        # Setup: create workspace group and workspace
        cls.manager = workspace_utils.get_workspace_manager()
        us_regions = [x for x in cls.manager.regions if "US" in x.name]
        cls.password = secrets.token_urlsafe(20) + "-x&$"
        name = clean_name(secrets.token_urlsafe(20)[:20])
        cls.workspace_group = cls.manager.create_workspace_group(
            f"wg-test-{name}",
            region=random.choice(us_regions).id,
            admin_password=cls.password,
            firewall_ranges=["0.0.0.0/0"],
        )
        try:
            cls.workspace = cls.workspace_group.create_workspace(
                f"ws-test-{name}-x",
                wait_on_active=True,
            )
        except Exception:
            cls.workspace_group.terminate(force=True)
            raise

    @classmethod
    def teardown_class(cls):
        if cls.workspace_group is not None:
            cls.workspace_group.terminate(force=True)
        cls.workspace_group = None
        cls.workspace = None
        cls.manager = None
        cls.password = None

    def test_workspace_groups_info(self):
        resp = workspace_groups_info()
        assert resp["status"] == "success"

        wsg = resp["data"]

        group_ids = [g["workspaceGroupID"] for g in wsg]
        group_names = [g["name"] for g in wsg]

        assert type(self).workspace_group.id in group_ids
        assert type(self).workspace_group.name in group_names

    def test_workspaces_info(self):
        resp = workspaces_info(type(self).workspace_group.id)
        assert resp["status"] == "success"

        ws = resp["data"]

        assert all(w["workspaceGroupID"] == type(self).workspace_group.id for w in ws)

        workspace_ids = [w["workspaceID"] for w in ws]
        workspace_names = [w["name"] for w in ws]

        assert type(self).workspace.id in workspace_ids
        assert type(self).workspace.name in workspace_names

    def test_resume_workspace(self):
        # First suspend the workspace to have something to resume
        type(self).workspace.suspend(wait_on_suspended=True)

        # Verify workspace is suspended
        type(self).workspace.refresh()
        assert type(self).workspace.state == "SUSPENDED"

        # Now test the resume_workspace function
        resp = resume_workspace(type(self).workspace.id)
        assert resp["status"] == "success"
        assert "resumed successfully" in resp["message"]

        # Verify the response data
        assert resp["data"]["workspaceID"] == type(self).workspace.id
        assert resp["data"]["name"] == type(self).workspace.name
        assert resp["data"]["workspaceGroupID"] == type(self).workspace_group.id

        # Verify workspace is now active
        type(self).workspace.refresh()
        assert type(self).workspace.state == "ACTIVE"
