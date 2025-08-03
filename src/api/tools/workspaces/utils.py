import singlestoredb as s2
from src.config import config
from src.api.common import get_access_token, get_org_id


def get_workspace_manager():
    """
    Returns the workspace manager object using the workspace manager.
    """
    settings = config.get_settings()
    access_token = get_access_token()
    org_id = get_org_id()
    workspace_manager = s2.manage_workspaces(
        access_token=access_token,
        base_url=settings.s2_api_base_url,
        organization_id=org_id,
    )
    return workspace_manager
