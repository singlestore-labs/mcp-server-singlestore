import singlestoredb as s2
from src.config import config
from src.api.common import call_sdk_with_retry, get_access_token, get_org_id


def get_workspace_manager():
    """
    Returns the workspace manager object using the workspace manager.
    """
    settings = config.get_settings()

    def _create():
        return s2.manage_workspaces(
            access_token=get_access_token(),
            base_url=settings.s2_api_base_url,
            organization_id=get_org_id(),
        )

    return call_sdk_with_retry(_create)
