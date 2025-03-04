import requests
from .config import SINGLESTORE_API_KEY, SINGLESTORE_API_BASE_URL


def __build_request(type: str, endpoint: str) -> str:
    def build_request_endpoint(endpoint: str) -> str:
        return f"{SINGLESTORE_API_BASE_URL}/v1/{endpoint}"
    
    # Headers with authentication
    headers = {
        "Authorization": f"Bearer {SINGLESTORE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    request_endpoint = build_request_endpoint(endpoint)

    request=None
    if type == "GET":
        request = requests.get(request_endpoint, headers=headers)
    elif type == "POST":
        request = requests.post(request_endpoint, headers=headers)
    elif type == "PUT":
        request = requests.put(request_endpoint, headers=headers)
    elif type == "DELETE":
        request = requests.delete(request_endpoint, headers=headers)
    else:
        raise ValueError(f"Unsupported request type: {type}")
    return request.json()
    

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
    }
]
