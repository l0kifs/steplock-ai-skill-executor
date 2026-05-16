"""Wiring root — instantiates and runs the MCP server."""

from steplock.entry_points.mcp.server import mcp

if __name__ == "__main__":
    mcp.run()
