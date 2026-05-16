"""Filesystem-backed and in-memory skill registry implementations."""

from __future__ import annotations

from pathlib import Path

import yaml

from steplock.application.skill.ports import ISkillRegistry

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


class SkillsRegistry(ISkillRegistry):
    """Reads skill paths from ~/.steplock/skills-registry.yaml.

    Creates the file (and parent directory) automatically on first access.
    """

    def __init__(self, registry_path: Path) -> None:
        self._registry_path = registry_path

    def ensure_initialized(self) -> None:
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._registry_path.exists():
            self._registry_path.write_text(_REGISTRY_TEMPLATE)

    def list_skill_paths(self) -> list[str]:
        self.ensure_initialized()
        with open(self._registry_path) as f:
            data = yaml.safe_load(f) or {}
        return [str(p) for p in (data.get("skills") or [])]


class CompositeSkillRegistry(ISkillRegistry):
    """Merges skill paths from multiple registries."""

    def __init__(self, registries: list[ISkillRegistry]) -> None:
        self._registries = registries

    def ensure_initialized(self) -> None:
        for registry in self._registries:
            registry.ensure_initialized()

    def list_skill_paths(self) -> list[str]:
        paths: list[str] = []
        for registry in self._registries:
            paths.extend(registry.list_skill_paths())
        return paths


class InMemorySkillRegistry(ISkillRegistry):
    """In-memory registry for testing."""

    def __init__(self, paths: list[str]) -> None:
        self._paths = paths

    def ensure_initialized(self) -> None:
        pass

    def list_skill_paths(self) -> list[str]:
        return list(self._paths)
