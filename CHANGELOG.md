# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-05-16

### Added
- `helpers` field on steps in `SKILL.yaml` — declare per-step helper scripts agents can invoke during execution
- `run_helper_script` MCP tool — agents can run helper scripts by name with optional arguments, receiving `stdout`, `stderr`, and `exit_code`
- `helper_scripts` field in `start_skill` and `submit_step_output` responses — lists available helper names for the current step

### Fixed
- Helper subprocess no longer inherits the MCP server's stdin pipe, preventing indefinite hangs on stdio transports
- Removed duplicate `submit_step_output` method in `SkillExecutionService`

## [0.1.0] - 2026-05-16

### Added
- MCP server with three tools: `list_skills`, `start_skill`, `submit_step_output`
- Step-by-step skill execution with session tracking
- YAML-based skill definitions with ordered steps
- Optional Python verification scripts per step for output validation
- Composite skill registry that merges project-level and user-level skill registries
- Support for `uvx steplock` installation and execution

[0.2.0]: https://github.com/l0kifs/steplock-ai-skill-executor/releases/tag/v0.2.0
[0.1.0]: https://github.com/l0kifs/steplock-ai-skill-executor/releases/tag/v0.1.0
