# VS Code MCP Setup — Developer Guide

How to connect the StepLock MCP server to VS Code when running from a local source checkout (i.e. without a PyPI installation).

---

## Prerequisites

- [uv](https://github.com/astral-sh/uv) installed
- Project dependencies synced: `uv sync`

---

## mcp.json configuration

Open (or create) `.vscode/mcp.json` in the project root to scope the config to this workspace, or run **MCP: Open User Configuration** from the Command Palette (`Ctrl+Shift+P`) to configure it globally.

```json
{
  "servers": {
    "steplock": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "-m", "steplock.entry_points.main"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

`uv run` ensures the server uses the project's local virtual environment. `cwd` is set to the workspace root so uv can locate `pyproject.toml`.

> **End users** should use `uvx steplock` instead — see the [quickstart](../product/quickstart.md).

---

## Starting and restarting the server

After saving `mcp.json`, VS Code detects the change and prompts you to trust and start the server. To start or restart it manually:

```
Command Palette (Ctrl+Shift+P) → MCP: List Servers → steplock → Start Server
```

Or use the gear icon next to **steplock** in the **MCP SERVERS — INSTALLED** section of the Extensions view.

---

## Verifying the server is running

1. Open **Copilot Chat** (`Ctrl+Alt+I`).
2. Click **Select tools** and confirm `list_skills`, `start_skill`, and `submit_step_output` are listed.

---

## Viewing server logs

Run `MCP: List Servers → steplock → Show Output` from the Command Palette. The output panel shows server stdout/stderr, which is useful for diagnosing startup errors or import failures.

---

## Running tests

```bash
uv run pytest tests/e2e/ -v
```

Tests use an in-memory transport — no running server instance is required.
