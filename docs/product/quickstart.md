# StepLock — Quick Start Guide

## What is StepLock?

StepLock is an MCP server that acts as a **gatekeeper runtime** between your AI agent and a skill definition. Instead of letting the agent interpret an entire skill freely, StepLock:

- Delivers **one step at a time**
- Requires the agent to **submit output** before moving on
- Runs **verification scripts** to check that output
- Only advances when verification passes

The result is reliable, auditable skill execution regardless of which LLM is driving the agent.

---

## Installation

```bash
pip install steplock
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv add steplock
```

---

## Running the Server

```bash
python -m steplock.entry_points.main
```

This starts the MCP server on STDIO (default), ready to accept connections from any MCP-compatible client.

---

## Registering Skills

StepLock discovers skills through a registry file at `~/.steplock/skills-registry.yaml`.

The file is created automatically the first time the server starts. Add an entry for each skill directory:

```yaml
# ~/.steplock/skills-registry.yaml
skills:
  - /home/user/my-skills/my-skill
  - /home/user/my-skills/another-skill
```

Each path must point to a directory that contains a `SKILL.yaml` file. The agent only ever sees skill **names** — filesystem paths are never exposed.

---

## Defining a Skill

Create a directory for your skill with the following structure:

```
my-skill/
├── SKILL.yaml
├── steps/
│   ├── step1.md
│   └── step2.md
└── scripts/
    └── verify_step1.py
```

### SKILL.yaml

```yaml
name: my-skill
description: When and why to use this skill.

steps:
  - id: step-1
    instruction: steps/step1.md     # path to a file, or inline text
    verify: scripts/verify_step1.py # optional
    on_fail: retry                  # retry | abort (default: abort)

  - id: step-2
    instruction: steps/step2.md
    # no verify — output is accepted immediately
```

### Step instructions

A step instruction can be:

- **A file path** (relative to the skill directory) — StepLock reads the file and sends its contents to the agent.
- **An inline string** — The string itself is sent to the agent as-is.

### Verification scripts

A verify script receives the agent's submitted output via **stdin** and must exit with:

- **Code 0** — output is accepted, execution advances to the next step.
- **Non-zero code** — output is rejected; anything printed to stdout/stderr is returned to the agent as guidance.

```python
# scripts/verify_step1.py
import sys

output = sys.stdin.read()

if "DONE" not in output:
    print("The output must contain the word DONE.")
    sys.exit(1)
```

Any executable works as a verify script (Python, Bash, Node.js, etc.) as long as it follows the exit-code contract.

---

## on_fail Modes

| Value | Behaviour |
|-------|-----------|
| `retry` | The same step instruction is re-sent together with the script's failure output. The agent can try again. |
| `abort` | Execution halts and the script's failure output is returned. |

If `on_fail` is omitted, it defaults to `abort`.

---

## Using the MCP Tools

StepLock exposes three tools to the connected agent.

### `list_skills`

Returns all skills available in the registry. Call this first to discover what skills are available.

**Response**

```json
[
  { "name": "my-skill",      "description": "When and why to use this skill." },
  { "name": "another-skill", "description": "..." }
]
```

### `start_skill`

Loads a skill by name and returns the first step.

| Parameter | Type | Description |
|-----------|------|-------------|
| `skill_name` | `string` | Name of the skill as returned by `list_skills` |

**Response**

```json
{
  "session_id": "3e4f...",
  "step_id": "step-1",
  "instruction": "Contents of steps/step1.md"
}
```

### `submit_step_output`

Submits the agent's output for the current step.

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | `string` | Session identifier from `start_skill` |
| `output` | `string` | The output the agent produced for this step |

**Possible responses**

```json
{ "status": "next_step", "step_id": "step-2", "instruction": "..." }
{ "status": "completed" }
{ "status": "retry",   "step_id": "step-1", "instruction": "...", "message": "guidance from verify script" }
{ "status": "aborted", "message": "guidance from verify script" }
```

---

## Minimal Example

```
hello-skill/
└── SKILL.yaml
```

```yaml
# SKILL.yaml
name: hello-skill
description: A single-step skill with no verification.

steps:
  - id: greet
    instruction: Say hello to the user.
```

Add the skill to the registry:

```yaml
# ~/.steplock/skills-registry.yaml
skills:
  - /path/to/hello-skill
```

Connecting an agent:

1. Agent calls `list_skills` and sees `hello-skill` in the response.
2. Agent calls `start_skill` with `skill_name = "hello-skill"`.
3. Agent receives `{ "session_id": "...", "step_id": "greet", "instruction": "Say hello to the user." }`.
4. Agent executes the instruction and calls `submit_step_output` with its output.
5. Agent receives `{ "status": "completed" }`.

A single step with no `verify` field behaves identically to an Anthropic-model skill, so existing skills can be adopted with zero changes.

---

## Configuration Reference

| SKILL.yaml field | Required | Default | Description |
|-----------------|----------|---------|-------------|
| `name` | Yes | — | Human-readable skill name |
| `description` | No | `""` | When and why to use this skill |
| `steps[].id` | Yes | — | Unique step identifier |
| `steps[].instruction` | Yes | — | File path or inline instruction text |
| `steps[].verify` | No | — | Path to verification script (relative to skill dir) |
| `steps[].on_fail` | No | `abort` | `retry` or `abort` |

---

## Backward Compatibility

A skill defined as a single step with no `verify` field is **identical** to an Anthropic-model skill. Existing skills can be wrapped in a `SKILL.yaml` with no behavioural changes.

---

## Connecting to VS Code

Add the following to your `mcp.json` (run **MCP: Open User Configuration** from the Command Palette):

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

Save the file, accept the trust dialog, and the three tools (`list_skills`, `start_skill`, `submit_step_output`) become available in Copilot Chat.

