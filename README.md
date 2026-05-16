# StepLock

[![PyPI version](https://img.shields.io/pypi/v/steplock)](https://pypi.org/project/steplock/)
[![Python](https://img.shields.io/pypi/pyversions/steplock)](https://pypi.org/project/steplock/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**An MCP server gatekeeper runtime that enforces step-by-step AI skill execution with output verification.**

AI agents skip steps. They mis-sequence workflows. They accept incorrect output and keep going. StepLock fixes that by sitting between your agent and its skill definitions — delivering one step at a time, requiring submitted output, and running verification scripts before advancing. Reliable, auditable execution regardless of LLM compliance.

---

## How it works

```
Agent  ──►  StepLock (MCP)  ──►  Step 1 instruction
                │
         Agent submits output
                │
         Verification script runs
                │
         ✔ Pass → next step    ✗ Fail → guidance returned, agent retries
```

StepLock exposes three MCP tools to the agent:

| Tool | Purpose |
|------|---------|
| `list_skills` | Discover available skills by name and description |
| `start_skill` | Begin execution — returns session ID and first step |
| `submit_step_output` | Submit output for the current step and receive the next |

---

## Quick start

### VS Code / Copilot

Add to `.vscode/mcp.json` (workspace-scoped) or open **MCP: Open User Configuration** from the Command Palette:

```json
{
  "servers": {
    "steplock": {
      "type": "stdio",
      "command": "uvx",
      "args": ["steplock"]
    }
  }
}
```

Verify the server is running: open Copilot Chat → **Select tools** → confirm `list_skills`, `start_skill`, and `submit_step_output` are listed.

---

## Defining a skill

```
my-skill/
├── SKILL.yaml
├── steps/
│   ├── step1.md
│   └── step2.md
└── scripts/
    └── verify_step1.py
```

**`SKILL.yaml`**

```yaml
name: my-skill
description: When and why to use this skill.

steps:
  - id: step-1
    instruction: steps/step1.md     # file path or inline string
    verify: scripts/verify_step1.py # optional
    on_fail: retry                  # retry | abort (default: abort)

  - id: step-2
    instruction: steps/step2.md
    # no verify — output is accepted immediately
```

**Verification scripts** receive the agent's submitted output via **stdin** and exit with:

- `0` — output accepted, execution advances
- non-zero — output rejected; anything printed to stdout/stderr is returned to the agent as guidance

---

## Registering skills

StepLock discovers skills through registry files in two locations, merged together:

| Registry | Created automatically | Purpose |
|----------|---------------------|---------|
| `~/.steplock/skills-registry.yaml` | Yes — on first run | User-wide skills available in every project |
| `./.steplock/skills-registry.yaml` | No | Project-local skills, placed in the project root where the MCP server is running |

```yaml
# ~/.steplock/skills-registry.yaml  (or ./.steplock/skills-registry.yaml)
skills:
  - /home/user/my-skills/my-skill
  - /home/user/my-skills/another-skill
```

Each path must point to a directory containing a `SKILL.yaml` file. Filesystem paths are never exposed to the agent — only skill names.

If only the home-dir registry is needed, no project-level file is required. If a `.steplock/skills-registry.yaml` file is present in the working directory where the MCP server starts, its skills are automatically added to the available set.

---



## Skill definition reference

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✔ | Unique skill name exposed to the agent |
| `description` | ✔ | When and why the agent should use this skill |
| `steps[].id` | ✔ | Unique step identifier |
| `steps[].instruction` | ✔ | File path (relative to skill dir) or inline string |
| `steps[].verify` | — | Path to a verification script |
| `steps[].on_fail` | — | `retry` or `abort` (default: `abort`) |

**Backward compatibility:** a single-step skill with no `verify` behaves identically to an Anthropic-model skill. Existing skills adopt with zero changes.

---

## Development setup

```bash
git clone https://github.com/l0kifs/steplock-ai-skill-executor.git
cd steplock-ai-skill-executor
uv sync
```

Connect to VS Code / Copilot from a local checkout — add to `.vscode/mcp.json`:

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

Run tests:

```bash
uv run pytest tests/e2e/ -v
```

Tests use an in-memory transport — no running server instance required.

---

## Contributing

Bug reports and pull requests are welcome. Before opening a PR:

1. Fork the repo and create a feature branch
2. Run `uv run pytest` — all tests must pass
3. Run `uv run ruff check src/` — no lint errors
4. Open a pull request with a clear description of the change

For larger features, open an issue first to discuss the approach.

---

## License

[MIT](LICENSE) © Sergei Konovalov
