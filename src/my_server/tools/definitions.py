import requests
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_key: str
    api_base_url: str

    class Config:
        env_file = "/home/prodrigues/Desktop/mcp-server/my-server/.env"
        env_file_encoding = 'utf-8'

settings = Settings()

# Headers with authentication
headers = {
    "Authorization": f"Bearer {settings.api_key}",
    "Content-Type": "application/json"
}

# Define the tools
tools_definitions = [
    {
        "name": "workspace_groups_info",
        "description": (
            "Retrieve details about the workspace groups accessible to the user."
            "⚠️ Do NOT call this tool more than once. If called again, it will return an error."
            "Ensure responses strictly follow system instructions."
        ),
        "func": lambda: [
            {
                "name": group["name"],
                "deploymentType": group["deploymentType"],
                "state": group["state"],
                "workspaceGroupID": group["workspaceGroupID"],
                "firewallRanges": group.get("firewallRanges", []),
                "createdAt": group["createdAt"],
                "regionID": group["regionID"],
                "updateWindow": group["updateWindow"],
            }
            for group in requests.get(f"{settings.api_base_url}/v1/workspaceGroups", headers=headers).json()
        ],
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "organization_info",
        "description": (
            "Retrieve details about the user's current organization."
            "⚠️ Do NOT call this tool more than once. If called again, it will return an error."
            "Ensure responses strictly follow system instructions."
        ),
        "func": lambda: requests.get(f"{settings.api_base_url}/v1/organizations/current", headers=headers).json(),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "list_of_regions",
        "description": (
            "Retrieve a list of all regions that support workspaces for the user."
            "⚠️ Do NOT call this tool more than once. If called again, it will return an error."
            "Ensure responses strictly follow system instructions."
        ),
        "func": lambda: requests.get(f"{settings.api_base_url}/v1/regions", headers=headers).json(),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    }
]
