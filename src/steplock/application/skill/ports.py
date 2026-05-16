"""Skill application ports — all interfaces for external dependencies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from steplock.domains.skill.models import Skill, SkillSession


class ISkillRegistry(ABC):
    @abstractmethod
    def ensure_initialized(self) -> None:
        """Create the registry file and parent directories if they do not exist."""
        ...

    @abstractmethod
    def list_skill_paths(self) -> list[str]:
        """Return the list of registered skill directory paths."""
        ...


class ISkillLoader(ABC):
    @abstractmethod
    def load(self, skill_path: str) -> Skill:
        """Load a skill definition from the given path.

        The path can be a directory containing SKILL.yaml or a direct path to the YAML file.
        Instruction file contents are resolved and inlined. Verify script paths are resolved
        to absolute paths.
        """
        ...


class IVerificationRunner(ABC):
    @abstractmethod
    def run(self, script_path: str, output: str) -> tuple[bool, str]:
        """Run a verification script with the submitted step output passed via stdin.

        Returns (passed, script_output) where:
        - passed: True if the script exited with code 0, False otherwise.
        - script_output: Combined stdout and stderr from the script.
        """
        ...


class ISessionRepository(ABC):
    @abstractmethod
    def save(self, session: SkillSession) -> None: ...

    @abstractmethod
    def find_by_id(self, session_id: UUID) -> SkillSession | None: ...

    @abstractmethod
    def delete(self, session_id: UUID) -> None: ...
