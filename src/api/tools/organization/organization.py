"""Organization tools for SingleStore MCP server."""

import time
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from mcp.server.fastmcp import Context

import src.api.tools.organization.utils as utils
from src.config import config
from src.api.common import query_graphql_organizations
from src.utils.elicitation import try_elicitation, ElicitationError
from src.logger import get_logger

# Set up logger for this module
logger = get_logger()


def organization_info() -> dict:
    """
    Retrieve information about the current user's organization in SingleStore.

    Returns organization details including:
    - orgID: Unique identifier for the organization
    - name: Organization display name
    """
    start_time = time.time()
    settings = config.get_settings()
    user_id = config.get_user_id()
    settings.analytics_manager.track_event(
        user_id, "tool_calling", {"name": "organization_info"}
    )

    org = utils.fetch_organization()
    execution_time = (time.time() - start_time) * 1000

    return {
        "status": "success",
        "message": f"Retrieved organization information for '{org.name}'",
        "data": {
            "orgID": org.id,
            "name": org.name,
        },
        "metadata": {
            "execution_time_ms": round(execution_time, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


async def choose_organization(ctx: Context) -> dict:
    """
    List all available SingleStore organizations your account has access to.

    After logging in, this tool must be called first to identify which organization
    your queries should run against. Returns a list of organizations with:

    - orgID: Unique identifier for the organization
    - name: Display name of the organization

    Use this tool when:
    1. Starting a new session to see available organizations
    2. To verify permissions across multiple organizations
    3. Before switching context to a different organization

    The tool will:
    1. List all available organizations
    2. If multiple organizations exist, prompt the user to select one
    3. If only one organization exists, automatically select it
    4. Update the context to use the selected organization
    """

    settings = config.get_settings()
    user_id = config.get_user_id()
    # Track tool call event
    settings.analytics_manager.track_event(
        user_id, "tool_calling", {"name": "choose_organization"}
    )

    logger.debug("choose_organization called")
    logger.debug(f"Is remote: {settings.is_remote}")

    try:
        logger.debug("Calling query_graphql_organizations...")
        # Get the list of organizations via GraphQL
        organizations = query_graphql_organizations()
        logger.debug(f"Retrieved {len(organizations)} organizations")

        if not organizations:
            logger.warning("No organizations available")
            return {
                "status": "error",
                "message": "No organizations available for your account. Please check your access permissions.",
            }

        selected_org = None

        # If only one organization is available, select it automatically
        if len(organizations) == 1:
            selected_org = organizations[0]
        else:
            # For multiple organizations, use elicitation to let the user choose
            class OrganizationChoice(BaseModel):
                """Schema for collecting organization selection."""

                organizationID: str = Field(
                    description="Select the organization ID to use",
                    choices=[org["orgID"] for org in organizations],
                )

            # Format the organization list for display
            org_list = "\n".join(
                [f"- ID: {org['orgID']} ({org['name']})" for org in organizations]
            )

            elicit_result, error = await try_elicitation(
                ctx=ctx,
                message=f"""**Available SingleStore Organizations:**\n\n{org_list}\n\nPlease select the organization ID you want to use.""",
                schema=OrganizationChoice,
            )

            if error == ElicitationError.NOT_SUPPORTED:
                # Client doesn't support elicitation, return list and wait for next prompt
                await ctx.info(
                    "This client doesn't support interactive organization selection."
                    " Please wait for the next prompt to provide the organization ID and call set_organization tool."
                )
                return {
                    "status": "pending_selection",
                    "message": "Please provide the organization ID in your next request",
                    "data": {
                        "organizations": organizations,
                        "count": len(organizations),
                    },
                }

            if elicit_result.status == "success" and elicit_result.data:
                # Find the matching organization from the selection
                selected_org_id = elicit_result.data.organizationID
                if selected_org_id:
                    for org in organizations:
                        if org["orgID"] == selected_org_id:
                            selected_org = org
                            break
            elif elicit_result.status == "cancelled":
                return {
                    "status": "cancelled",
                    "message": "Organization selection was cancelled",
                    "data": {
                        "organizations": organizations,
                        "count": len(organizations),
                    },
                }

        # Set the selected organization in settings
        if selected_org:
            settings.org_id = selected_org["orgID"]

            return {
                "status": "success",
                "message": f"Successfully selected organization: {selected_org['name']} (ID: {selected_org['orgID']})",
                "data": {
                    "organization": selected_org,
                    "count": len(organizations),
                },
                "metadata": {
                    "total_organizations": len(organizations),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": user_id,
                },
            }
        else:
            return {
                "status": "error",
                "message": "No organization was selected",
                "data": {
                    "organizations": organizations,
                    "count": len(organizations),
                },
            }

    except Exception as e:
        logger.error(f"Error retrieving organizations: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to retrieve organizations: {str(e)}",
            "errorCode": "ORGANIZATION_QUERY_FAILED",
            "errorDetails": {"exception_type": type(e).__name__},
        }


async def set_organization(ctx: Context, organization_id: str) -> dict:
    """
    Set the current organization after retrieving the list from choose_organization.
    This tool should only be used when the client doesn't support elicitation.

    Args:
        organization_id: The ID of the organization to select, as obtained from the
                       choose_organization tool's response.

    Returns:
        Dictionary with selected organization details

    Important:
    - This tool should only be called after choose_organization returns a 'pending_selection' status
    - The organization_id must be one of the IDs returned by choose_organization

    Example flow:
    1. Call choose_organization first
    2. If it returns 'pending_selection', get the organization ID from the list
    3. Call set_organization with the chosen ID
    """
    settings = config.get_settings()
    user_id = config.get_user_id()
    # Track tool call event
    settings.analytics_manager.track_event(
        user_id,
        "tool_calling",
        {"name": "set_organization", "organization_id": organization_id},
    )

    logger.debug(f"Setting organization ID: {organization_id}")

    try:
        # Get the list of organizations to validate the selection
        organizations = query_graphql_organizations()

        # Find the selected organization
        selected_org = next(
            (org for org in organizations if org["orgID"] == organization_id), None
        )

        if not selected_org:
            available_orgs = ", ".join(org["orgID"] for org in organizations)
            return {
                "status": "error",
                "message": f"Organization ID '{organization_id}' not found. Available IDs: {available_orgs}",
                "errorCode": "INVALID_ORGANIZATION",
                "errorDetails": {
                    "provided_id": organization_id,
                    "available_ids": [org["orgID"] for org in organizations],
                },
            }

        # Set the selected organization in settings
        if hasattr(settings, "org_id"):
            settings.org_id = selected_org["orgID"]
        else:
            setattr(settings, "org_id", selected_org["orgID"])

        await ctx.info(
            f"Organization set to: {selected_org['name']} (ID: {selected_org['orgID']})"
        )

        return {
            "status": "success",
            "message": f"Successfully set organization to: {selected_org['name']} (ID: {selected_org['orgID']})",
            "data": {
                "organization": selected_org,
            },
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
            },
        }

    except Exception as e:
        logger.error(f"Error setting organization: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to set organization: {str(e)}",
            "errorCode": "ORGANIZATION_SET_FAILED",
            "errorDetails": {"exception_type": type(e).__name__},
        }
