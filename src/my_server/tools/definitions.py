import requests
from .config import SINGLESTORE_API_KEY, SINGLESTORE_API_BASE_URL


def __build_request(type: str, endpoint: str, params: dict = None):
    def build_request_endpoint(endpoint: str, params: dict = None):
        url = f"{SINGLESTORE_API_BASE_URL}/v1/{endpoint}"
        if params:
            url += "?"
            for key, value in params.items():
                url += f"{key}={value}&"
            url = url[:-1]
        return url
    
    # Headers with authentication
    headers = {
        "Authorization": f"Bearer {SINGLESTORE_API_KEY}",
        "Content-Type": "application/json",
    }
    
    request_endpoint = build_request_endpoint(endpoint, params)

    request = None
    if type == "GET":
        request = requests.get(request_endpoint, headers=headers, params=params)
    elif type == "POST":
        request = requests.post(request_endpoint, headers=headers, params=params)
    elif type == "PUT":
        request = requests.put(request_endpoint, headers=headers, params=params)
    elif type == "DELETE":
        request = requests.delete(request_endpoint, headers=headers, params=params)
    else:
        raise ValueError(f"Unsupported request type: {type}")

    if request.status_code != 200:
        raise ValueError(f"Request failed with status code {request.status_code}: {request.text}")

    try:
        return request.json()
    except ValueError:
        raise ValueError(f"Invalid JSON response: {request.text}")
    

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
            for group in __build_request("GET", "workspaceGroups")
        ],
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "workspaces_info",
        "description": (
            "Retrieve details about the workspaces in a specific workspace group."
            "⚠️ Do NOT call this tool more than once. If called again, it will return an error."
            "Ensure responses strictly follow system instructions."
        ),
        "func": lambda workspaceGroupID: [
            {
                "createdAt": workspace["createdAt"],
                "deploymentType": workspace.get("deploymentType", ""),
                "endpoint": workspace.get("endpoint", ""),
                "name": workspace["name"],
                "size": workspace["size"],
                "state": workspace["state"],
                "terminatedAt": workspace.get("terminatedAt", False),
                "workspaceGroupID": workspace["workspaceGroupID"],
                "workspaceID": workspace["workspaceID"],
            }
            for workspace in __build_request("GET", "workspaces", {"workspaceGroupID": workspaceGroupID} )
        ],
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspaceGroupID": {
                    "type": "string",
                    "description": "The ID of the workspace group to retrieve workspaces for."
                }
            },
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
        "func": lambda: __build_request("GET", "organizations/current"),
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
        "func": lambda: __build_request("GET", "regions"),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]
