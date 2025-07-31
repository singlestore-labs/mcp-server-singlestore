import singlestoredb as s2
from src.api.common import get_access_token, get_org_id
from src.config import config


def fetch_organization():
    """
    Returns the organization object using the workspace manager.
    """
    settings = config.get_settings()
    workspace_manager = s2.manage_workspaces(
        access_token=get_access_token(),
        base_url=settings.s2_api_base_url,
        organization_id=get_org_id(),
    )
    return workspace_manager.organization
