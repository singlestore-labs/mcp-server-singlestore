import singlestoredb as s2
from src.api.common import call_sdk_with_retry, get_access_token, get_org_id
from src.config import config


def fetch_organization():
    """
    Returns the organization object using the workspace manager.
    """

    def _fetch():
        settings = config.get_settings()
        workspace_manager = s2.manage_workspaces(
            access_token=get_access_token(),
            base_url=settings.s2_api_base_url,
            organization_id=get_org_id(),
        )
        return workspace_manager.organization

    return call_sdk_with_retry(_fetch)
