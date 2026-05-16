# Skill Execution Framework — BRD

## Problem

Current agent skill architecture (Anthropic model) relies entirely on the LLM to:
- Follow step order and subflows correctly
- Verify output of each step before proceeding

In practice agents skip steps, mis-sequence subflows, and accept incorrect outputs. No enforcement exists outside the LLM's own judgment.

## Goal

A framework that — when used correctly by skill creators — produces stable and reliable agent execution regardless of LLM compliance tendencies.

## Solution

An MCP server acting as a **gatekeeper runtime** between the agent and the skill definition.

- Provides the agent **one step at a time**
- Requires the agent to **submit output** before advancing
- Runs **verification scripts** defined by the skill creator
- Returns the next step only after verification passes

The MCP server enforces the flow. The LLM executes instructions within each step.

## Skill Definition Format

```yaml
name: skill-name
description: When and why to use this skill.

steps:
  - id: step-1
    instruction: path/to/step1.md       # or inline string
    verify: scripts/verify_step1.py     # optional
    on_fail: retry                      # optional: retry | abort

  - id: step-2
    instruction: path/to/step2.md
    # no verify — pass-through, identical to Anthropic model behavior
```

## Verification Contract

- The agent submits step output to the MCP server.
- MCP runs `verify` script with the submitted output.
- Script exits `0` = pass → server returns next step.
- Script exits non-zero = fail → server captures script output and applies `on_fail` behavior.

Script output on failure is **always returned to the agent** as guidance. Skill creators are responsible for writing meaningful failure messages in their verification scripts.

## on_fail Modes

| Mode | Behavior |
|------|----------|
| `retry` | Server re-sends the step instruction + script failure output. Agent retries with guidance. |
| `abort` | Server halts execution and returns script failure output to the agent. |

Default when `on_fail` is omitted: `abort`.

## Configuration Rules

| Config | Effect |
|--------|--------|
| `verify` omitted on a step | Step output accepted immediately, no check run |
| `on_fail` omitted | Defaults to `abort` |
| Single step, no `verify` | Identical behavior to current Anthropic skill model |
| All steps have no `verify` | Framework acts as a pure step sequencer only |

## Backward Compatibility

A skill defined as a single step with no `verify` field behaves identically to an Anthropic-model skill. Existing skills can be adopted into this framework with zero changes.

## File Structure

```
my-skill/
├── SKILL.yaml              # Skill definition (steps, verify paths, on_fail)
├── steps/
│   ├── step1.md            # Step instruction delivered to agent
│   └── step2.md
└── scripts/
    ├── verify_step1.py     # Verification script — exit 0 = pass, non-zero + output = guidance
    └── verify_step2.py
```

## Responsibilities

| Actor | Responsibility |
|-------|---------------|
| Framework (MCP server) | Step sequencing, output collection, script execution, on_fail routing |
| Skill creator | Writing step instructions, verification scripts, and guidance prompts |
| Agent | Executing step instructions, submitting output to MCP server |

## Out of Scope

- Parallel step execution
- Cross-skill orchestration
- Verification script language (any executable is valid)
- MCP server implementation details
