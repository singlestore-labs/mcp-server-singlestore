import src.api.tools.organization.utils as org_utils


def get_org_jobs_manager():
    org = org_utils.fetch_organization()
    if not org:
        raise ValueError("Organization not found. Please ensure you are logged in.")
    return org.jobs
