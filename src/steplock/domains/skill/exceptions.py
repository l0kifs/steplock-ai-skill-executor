"""Skill domain exceptions."""

from __future__ import annotations


class SkillNotFoundError(Exception):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Skill not found: {identifier}")
        self.identifier = identifier


class SessionNotFoundError(Exception):
    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session not found: {session_id}")
        self.session_id = session_id


class InvalidSkillDefinitionError(Exception):
    pass


class StepInstructionNotFoundError(Exception):
    def __init__(self, instruction_path: str) -> None:
        super().__init__(f"Step instruction file not found: {instruction_path}")
        self.instruction_path = instruction_path
