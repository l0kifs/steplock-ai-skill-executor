"""Skill application command structs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StartSkillCommand:
    skill_name: str


@dataclass
class SubmitStepOutputCommand:
    session_id: str
    output: str
