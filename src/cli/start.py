from src.config import app_config, AuthMethod
import os


def register_start_command(subparsers):
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


def handle_start_command(args, mcp):
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
        app_config.server_mode = "stdio"
    else:
        print(f"Running server with protocol {protocol.upper()}")
        app_config.server_mode = "stdio"
    mcp.settings.port = app_config.get_server_port()
    mcp.run(transport=protocol)
