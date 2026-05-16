"""Skill application command structs."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StartSkillCommand:
    skill_name: str


@dataclass
class SubmitStepOutputCommand:
    session_id: str
    output: str


@dataclass
class RunHelperScriptCommand:
    session_id: str
    script_name: str
    args: list[str] = field(default_factory=list)
