import pytest
import random
import secrets
import re


import tests.integration.tools.utils as utils
from src.api.tools.workspace_groups.workspace_groups import workspace_groups_info
from src.api.tools.workspaces.workspaces import workspaces_info


def clean_name(s):
    return re.sub(r"[^\w]", r"-", s).replace("_", "-").lower()


@pytest.mark.integration
class TestWorkspaceGroupAndWorkspaceIntegration:
    """Integration test for listing workspace groups and workspaces."""

    manager = None
    workspace_group = None
    workspace = None
    password = None

    @classmethod
    def setup_class(cls):
        # Setup: create workspace group and workspace
        cls.manager = utils.get_workspace_manager()
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

        wsg = resp["data"]["result"]

        group_ids = [g["workspaceGroupID"] for g in wsg]
        group_names = [g["name"] for g in wsg]

        assert type(self).workspace_group.id in group_ids
        assert type(self).workspace_group.name in group_names

    def test_workspaces_info(self):
        resp = workspaces_info(type(self).workspace_group.id)
        assert resp["status"] == "success"

        ws = resp["data"]["result"]

        assert all(w["workspaceGroupID"] == type(self).workspace_group.id for w in ws)

        workspace_ids = [w["workspaceID"] for w in ws]
        workspace_names = [w["name"] for w in ws]

        assert type(self).workspace.id in workspace_ids
        assert type(self).workspace.name in workspace_names
