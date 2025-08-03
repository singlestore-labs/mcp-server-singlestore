import singlestoredb as s2
from src.config import config
from src.api.common import get_access_token, get_org_id
import src.api.tools.workspaces.utils as workspace_utils


def get_file_manager():
    settings = config.get_settings()
    access_token = get_access_token()
    org_id = get_org_id()
    file_manager = s2.manage_files(
        access_token=access_token,
        base_url=settings.s2_api_base_url,
        organization_id=org_id,
    )
    return file_manager


def get_organization():
    """
    Returns the organization object using the workspace manager.
    """
    workspace_manager = workspace_utils.get_workspace_manager()
    return workspace_manager.organization
