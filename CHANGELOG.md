# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] - 2026-05-21

### Fixed
- Added missing `[project.scripts]` entry to `pyproject.toml` so that `uvx steplock` correctly finds and runs the MCP server executable

## [0.2.0] - 2026-05-16

### Added
- `helpers` field on steps in `SKILL.yaml` — declare per-step helper scripts agents can invoke during execution
- `run_helper_script` MCP tool — agents can run helper scripts by name with optional arguments, receiving `stdout`, `stderr`, and `exit_code`
- `helper_scripts` field in `start_skill` and `submit_step_output` responses — lists available helper names for the current step

## [0.1.0] - 2026-05-16

### Added
- MCP server with three tools: `list_skills`, `start_skill`, `submit_step_output`
- Step-by-step skill execution with session tracking
- YAML-based skill definitions with ordered steps
- Optional Python verification scripts per step for output validation
- Composite skill registry that merges project-level and user-level skill registries
- Support for `uvx steplock` installation and execution

[0.2.1]: https://github.com/l0kifs/steplock-ai-skill-executor/releases/tag/v0.2.1
[0.2.0]: https://github.com/l0kifs/steplock-ai-skill-executor/releases/tag/v0.2.0
[0.1.0]: https://github.com/l0kifs/steplock-ai-skill-executor/releases/tag/v0.1.0
