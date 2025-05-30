from argparse import ArgumentParser
import sys
from scripts.init import init_command
from auth.local_auth import get_authentication_token


def register_init_command(subparsers: ArgumentParser):
    parser = subparsers.add_parser("init", help="Initialize client configuration")
    parser.add_argument(
        "api_key",
        nargs="?",
        help="SingleStore API key (optional, will use web auth if not provided)",
    )
    parser.add_argument(
        "--client",
        default="claude",
        choices=["claude", "cursor"],
        help="LLM client to configure (default: claude)",
    )
    parser.set_defaults(func=handle_init_command)


def handle_init_command(args):
    api_key = getattr(args, "api_key", None)
    auth_token = None
    if not api_key:
        auth_token = get_authentication_token()
        if not auth_token:
            print("No API key provided and authentication failed.")
            sys.exit(1)
    sys.exit(init_command(api_key, auth_token, args.client))
