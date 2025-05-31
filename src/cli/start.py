import os

from argparse import ArgumentParser

from src.utils import logger
from src.config import app_config, AuthMethod
from src.auth.settings import ServerSettings
from src.auth import SingleStoreOAuthProvider
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from src.api.resources import resources, register_resources
from src.api.tools import tools, register_tools
from utils.middleware import apply_auth_middleware
from fastmcp import FastMCP
from src.server import app_lifespan  # Import app_lifespan for FastMCP
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response


def make_singlestore_callback_handler(oauth_provider: SingleStoreOAuthProvider):
    async def singlestore_callback_handler(request: Request) -> Response:
        code = request.query_params.get("code")
        state = request.query_params.get("state")

        if not code:
            raise HTTPException(400, "Missing code parameter")
        if not state:
            raise HTTPException(400, "Missing state parameter")

        try:
            redirect_uri = await oauth_provider.handle_singlestore_callback(code, state)
            return RedirectResponse(status_code=302, url=redirect_uri)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Unexpected error", exc_info=e)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "server_error",
                    "error_description": "Unexpected error",
                },
            )

    return singlestore_callback_handler


class MCPFactory:
    def __init__(
        self, settings: ServerSettings, oauth_provider: SingleStoreOAuthProvider
    ):
        self.settings = settings
        self.oauth_provider = oauth_provider

    def create_remote_mcp(self):
        mcp = FastMCP(
            "SingleStore MCP Server",
            lifespan=app_lifespan,
            auth_server_provider=self.oauth_provider,
            auth=self.settings.auth_settings,
            host=self.settings.host,
            port=self.settings.port,
        )
        register_resources(mcp, resources)
        public_tools = apply_auth_middleware(tools)
        register_tools(mcp, public_tools)

        # Register the callback handler with the captured oauth_provider
        mcp.custom_route("/callback", methods=["GET"])(
            make_singlestore_callback_handler(self.oauth_provider)
        )

        return mcp

    def create_local_mcp(self):
        raise NotImplementedError("Local MCP creation is not implemented yet.")


def register_start_command(subparsers: ArgumentParser):
    parser = subparsers.add_parser("start", help="Start the MCP server")
    parser.add_argument(
        "api_key",
        nargs="?",
        help="SingleStore API key (optional, will use web auth if not provided)",
    )
    parser.add_argument(
        "--protocol",
        default="stdio",
        choices=["stdio", "sse", "http"],
        help="Protocol to run the server on (default: stdio)",
    )
    parser.add_argument(
        "--port",
        default=8000,
        type=int,
        help="Port to run the server on (default: 8000) if protocol is sse",
    )
    parser.set_defaults(func=handle_start_command)


def handle_start_command(args):
    protocol = getattr(args, "protocol", "stdio")
    if getattr(args, "api_key", None):
        print(
            f"Using provided API key: {args.api_key[:10]}{'*' * (len(args.api_key) - 10)}"
        )
        app_config.set_auth_token(args.api_key, AuthMethod.API_KEY)
    elif os.getenv("SINGLESTORE_API_KEY"):
        print("Using API key from environment variable SINGLESTORE_API_KEY")
        app_config.set_auth_token(os.getenv("SINGLESTORE_API_KEY"), AuthMethod.API_KEY)

    if protocol == "sse":
        print(
            f"Running SSE server with protocol {protocol.upper()} on port {args.port}"
        )
        app_config.set_server_port(args.port)
        app_config.server_mode = "sse"
    elif protocol == "http":
        protocol = "streamable-http"
        print(
            f"Running Streamable HTTP server with protocol {protocol.upper()} on port {args.port}"
        )
        app_config.set_server_port(args.port)
        app_config.server_mode = "http"
    else:
        print(f"Running server with protocol {protocol.upper()}")
        app_config.server_mode = "stdio"

    client_registration_options = ClientRegistrationOptions(
        enabled=True,
    )

    settings = ServerSettings(
        host=app_config.settings.server_host,
        port=app_config.settings.server_port,
    )

    settings.auth_settings = AuthSettings(
        issuer_url=settings.server_url,
        required_scopes=[settings.mcp_scope],
        client_registration_options=client_registration_options,
    )

    oauth_provider = SingleStoreOAuthProvider(settings)

    mcp_factory = MCPFactory(settings, oauth_provider)

    if app_config.is_remote():
        print("Running in remote mode, MCP will connect to remote server.")
        mcp = mcp_factory.create_remote_mcp()
    else:
        print("Running in local mode, MCP will start a local server.")
        mcp = mcp_factory.create_local_mcp()

    mcp.run(transport=protocol)
