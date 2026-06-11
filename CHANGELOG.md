# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-06-11

### Added
- Auto-discovery of skills from `.steplock/` directories — StepLock now recursively scans `~/.steplock/` and `./.steplock/` for `SKILL.yaml` files without requiring explicit registry entries
- Folder support in `skills-registry.yaml` — registry entries can now point to a folder and all nested skill directories are discovered automatically
- Deduplication by skill name in `CompositeSkillRegistry` — when the same skill name appears in multiple registries, the project-local entry (`./.steplock/`) takes precedence over the user-wide entry (`~/.steplock/`)
- Circular symlink detection in directory scanning to prevent infinite loops
- Unit tests for `SkillsRegistry`, `CompositeSkillRegistry`, `_discover_skills_in_directory`, and `_resolve_registry_paths`
- E2E tests for auto-discovery, folder expansion, mixed registry entries, skill precedence, and deduplication

### Changed
- `SkillsRegistry` accepts an optional `auto_discover_base` parameter for recursive skill scanning
- `CompositeSkillRegistry.list_skill_paths()` now deduplicates by skill name instead of returning all paths verbatim
- Registry entries that are non-existent paths or non-directory files are skipped with a warning log instead of raising an error
- Updated pytest markers: `e2e` description clarified; added `integration` and `unit` markers

## [0.2.2] - 2026-05-21

### Changed
- Disabled FastMCP startup banner (`show_banner=False`) to keep server output clean
- Removed redundant `License :: OSI Approved :: MIT License` PyPI classifier from `pyproject.toml`

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

[0.3.0]: https://github.com/l0kifs/steplock-ai-skill-executor/releases/tag/v0.3.0
[0.2.2]: https://github.com/l0kifs/steplock-ai-skill-executor/releases/tag/v0.2.2
[0.2.1]: https://github.com/l0kifs/steplock-ai-skill-executor/releases/tag/v0.2.1
[0.2.0]: https://github.com/l0kifs/steplock-ai-skill-executor/releases/tag/v0.2.0
[0.1.0]: https://github.com/l0kifs/steplock-ai-skill-executor/releases/tag/v0.1.0
