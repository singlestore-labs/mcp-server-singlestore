def register_all_commands(subparsers):
    from src.cli import register_start_command, register_init_command

    register_start_command(subparsers)
    register_init_command(subparsers)
    # Add new command registrations here
