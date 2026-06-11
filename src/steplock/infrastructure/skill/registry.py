"""Filesystem-backed and in-memory skill registry implementations."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import yaml

from steplock.application.skill.ports import ISkillRegistry

_logger = logging.getLogger(__name__)

SKILL_YAML = "SKILL.yaml"

# ---------------------------------------------------------------------------
# Registry file template
# ---------------------------------------------------------------------------

_REGISTRY_TEMPLATE = """\
# StepLock Skills Registry
# Add paths to skill directories below. Each entry must point to a directory
# that contains a SKILL.yaml file.
#
# Example:
#   skills:
#     - /home/user/my-skills/git-commit
#     - /home/user/my-skills/code-review
skills: []
"""


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _discover_skills_in_directory(dir_path: Path, visited: set[str]) -> list[str]:
    """Recursively find all skill directories (containing SKILL.yaml) in a directory.

    Args:
        dir_path: Directory to scan recursively.
        visited: Set of already-visited real paths to prevent circular references.

    Returns:
        List of absolute paths to skill directories.
    """
    if not dir_path.exists() or not dir_path.is_dir():
        return []

    # Use realpath for cycle detection
    try:
        real = os.path.realpath(str(dir_path))
    except OSError:
        _logger.warning("Cannot resolve real path for: %s", dir_path)
        return []

    if real in visited:
        _logger.warning(
            "Skipping already-visited directory (potential cycle): %s",
            dir_path,
        )
        return []

    visited.add(real)

    skills: list[str] = []

    try:
        entries = list(dir_path.iterdir())
    except PermissionError as e:
        _logger.warning(
            "Permission denied scanning directory: %s: %s",
            dir_path,
            e,
        )
        return []
    except OSError as e:
        _logger.warning("OS error scanning directory: %s: %s", dir_path, e)
        return []

    for entry in entries:
        if entry.is_dir():
            # Check if this directory is a skill directory
            if (entry / SKILL_YAML).exists():
                skills.append(str(entry.resolve()))
            else:
                # Recursively scan subdirectory
                skills.extend(_discover_skills_in_directory(entry, visited))

    return skills


def _resolve_registry_paths(paths: list[str]) -> list[str]:
    """Process registry entries, expanding folders to individual skill paths.

    Args:
        paths: List of paths from registry file.

    Returns:
        List of resolved skill directory paths.
    """
    resolved: list[str] = []
    visited: set[str] = set()

    for path_str in paths:
        path = Path(path_str)

        if not path.exists():
            _logger.warning(
                "Registry path does not exist, skipping: %s",
                path_str,
            )
            continue

        if path.is_file():
            # If it's a SKILL.yaml file, use its parent directory
            if path.name == SKILL_YAML:
                resolved.append(str(path.parent.resolve()))
            else:
                _logger.warning(
                    "Registry entry is a file, not a directory, skipping: %s",
                    path_str,
                )
            continue

        # It's a directory - check if it's a skill directory itself first
        if (path / SKILL_YAML).exists():
            resolved.append(str(path.resolve()))
        else:
            # Recursively find all skills in it
            discovered = _discover_skills_in_directory(path, visited)
            resolved.extend(discovered)

    return resolved


# ---------------------------------------------------------------------------
# Registry Classes
# ---------------------------------------------------------------------------


class SkillsRegistry(ISkillRegistry):
    """Reads skill paths from a registry file and supports auto-discovery.

    Creates the file (and parent directory) automatically on first access.
    Optionally supports auto-discovery from a base directory (e.g., ~/.steplock).
    """

    def __init__(
        self,
        registry_path: Path,
        auto_discover_base: Path | None = None,
    ) -> None:
        """Initialize the registry.

        Args:
            registry_path: Path to the skills-registry.yaml file.
            auto_discover_base: Optional base directory for auto-discovery (e.g., ~/.steplock).
        """
        self._registry_path = registry_path
        self._auto_discover_base = auto_discover_base

    def ensure_initialized(self) -> None:
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._registry_path.exists():
            self._registry_path.write_text(_REGISTRY_TEMPLATE)

    def _auto_discover_skills(self) -> list[str]:
        """Scan _auto_discover_base for skills recursively.

        Returns:
            List of skill directory paths discovered.
        """
        if self._auto_discover_base is None:
            return []
        return _discover_skills_in_directory(self._auto_discover_base, set())

    def list_skill_paths(self) -> list[str]:
        """Return all skill paths: auto-discovered + explicit registry entries.

        Processes registry paths, expanding folder paths to individual skills.
        """
        self.ensure_initialized()

        # Get auto-discovered skills
        auto_discovered = self._auto_discover_skills()

        # Read explicit paths from registry
        with open(self._registry_path) as f:
            data = yaml.safe_load(f) or {}
        explicit_paths = [str(p) for p in (data.get("skills") or [])]

        # Process explicit paths, expanding folders
        resolved_explicit = _resolve_registry_paths(explicit_paths)

        # Combine auto-discovered and explicit paths
        return auto_discovered + resolved_explicit


class CompositeSkillRegistry(ISkillRegistry):
    """Merges skill paths from multiple registries with deduplication.

    Deduplication is by skill name, with later entries overriding earlier
    entries with the same name (project-local takes precedence).
    """

    def __init__(
        self,
        registries: list[ISkillRegistry],
        skill_names: dict[str, str] | None = None,
    ) -> None:
        """Initialize the composite registry.

        Args:
            registries: List of ISkillRegistry instances to merge.
            skill_names: Optional mapping of path -> skill name for deduplication.
        """
        self._registries = registries
        self._skill_names_cache: dict[str, str] | None = None

    def ensure_initialized(self) -> None:
        for registry in self._registries:
            registry.ensure_initialized()

    def _get_skill_name(self, skill_path: str) -> str:
        """Extract skill name from SKILL.yaml in the given path.

        Args:
            skill_path: Path to skill directory.

        Returns:
            Skill name or basename of path if not found.
        """
        skill_yaml_path = Path(skill_path) / SKILL_YAML
        if skill_yaml_path.exists():
            try:
                with open(skill_yaml_path) as f:
                    data = yaml.safe_load(f) or {}
                name = data.get("name")
                if name and isinstance(name, str):
                    return name
            except (yaml.YAMLError, OSError):
                pass
        return os.path.basename(skill_path.rstrip("/"))

    def list_skill_paths(self) -> list[str]:
        """Merge skill paths from all registries with deduplication by name.

        Later entries (from later registries) override earlier entries with
        the same skill name. This ensures project-local skills take precedence
        over user-wide skills.
        """
        # Use dict for deduplication by skill name (last wins)
        name_to_path: dict[str, str] = {}

        for registry in self._registries:
            paths = registry.list_skill_paths()
            for path in paths:
                name = self._get_skill_name(path)
                name_to_path[name] = path

        return list(name_to_path.values())


class InMemorySkillRegistry(ISkillRegistry):
    """In-memory registry for testing."""

    def __init__(self, paths: list[str]) -> None:
        self._paths = paths

    def ensure_initialized(self) -> None:
        pass

    def list_skill_paths(self) -> list[str]:
        return list(self._paths)
