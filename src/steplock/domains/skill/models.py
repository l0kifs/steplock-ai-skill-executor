"""Skill domain entities and value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID, uuid4


@dataclass
class Step:
    id: str
    instruction: str
    verify_script_path: str | None = None
    on_fail: Literal["retry", "abort"] = "abort"


@dataclass
class Skill:
    name: str
    description: str
    steps: list[Step]


@dataclass
class SkillSession:
    skill: Skill
    session_id: UUID = field(default_factory=uuid4)
    current_step_index: int = 0
    status: Literal["in_progress", "completed", "aborted"] = "in_progress"

    def get_current_step(self) -> Step | None:
        if self.status != "in_progress":
            return None
        if self.current_step_index >= len(self.skill.steps):
            return None
        return self.skill.steps[self.current_step_index]

    def advance(self) -> bool:
        """Advance to next step. Returns True if there are more steps, False if completed."""
        self.current_step_index += 1
        if self.current_step_index >= len(self.skill.steps):
            self.status = "completed"
            return False
        return True

    def abort(self) -> None:
        self.status = "aborted"
