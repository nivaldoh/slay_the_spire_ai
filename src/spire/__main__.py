"""Command-line entry point."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Slay the Spire experiment tools")
    parser.add_argument("--version", action="version", version="spire-agent 0.1.0")
    parser.parse_args()
    parser.print_help()


if __name__ == "__main__":
    main()
