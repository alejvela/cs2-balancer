"""Command-line adapter for the installed cs2-balancer distribution."""

import argparse
from collections.abc import Sequence
from importlib import metadata


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cs2-balancer", allow_abbrev=False)
    parser.add_argument(
        "--version", action="store_true", help="show the installed version and exit"
    )
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")
    for name, description in (
        ("balance", "Balance a roster of players."),
        ("tournament-report", "Generate a tournament report."),
    ):
        commands.add_parser(
            name, help=description, description=description, allow_abbrev=False
        )

    try:
        args = parser.parse_args(argv)
        if args.version and args.command is None:
            try:
                version = metadata.version("cs2-balancer")
            except metadata.PackageNotFoundError:
                version = "unknown (distribution metadata unavailable)"
            print(f"{parser.prog} {version}")
            return 0
        if args.command is None:
            parser.error("a command is required")
        parser.error(f"{args.command} is not available yet")
    except SystemExit as exit_status:
        # argparse uses SystemExit for both help and usage errors.
        return int(exit_status.code)
