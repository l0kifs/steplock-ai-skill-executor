# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-05-16

### Added
- MCP server with three tools: `list_skills`, `start_skill`, `submit_step_output`
- Step-by-step skill execution with session tracking
- YAML-based skill definitions with ordered steps
- Optional Python verification scripts per step for output validation
- Composite skill registry that merges project-level and user-level skill registries
- `git-commit-skill` bundled skill for guided Git commit workflow
- `hello-skill` example skill for testing and demonstration
- Support for `uvx steplock` installation and execution

[0.1.0]: https://github.com/l0kifs/steplock-ai-skill-executor/releases/tag/v0.1.0
