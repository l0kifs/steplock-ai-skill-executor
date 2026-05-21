"""Wiring root — instantiates and runs the MCP server."""

from steplock.entry_points.mcp.server import mcp


def main() -> None:
    mcp.run(show_banner=False)


if __name__ == "__main__":
    main()
