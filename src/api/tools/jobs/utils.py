import src.api.tools.organization.utils as org_utils
from src.api.common import call_sdk_with_retry


def get_org_jobs_manager():
    def _fetch_jobs_manager():
        org = org_utils.fetch_organization()
        if not org:
            raise ValueError("Organization not found. Please ensure you are logged in.")
        return org.jobs

    return call_sdk_with_retry(_fetch_jobs_manager)
