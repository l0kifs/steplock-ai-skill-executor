"""Skill domain events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class SkillStarted:
    session_id: UUID
    skill_name: str
    started_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class StepCompleted:
    session_id: UUID
    step_id: str
    completed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class SkillCompleted:
    session_id: UUID
    skill_name: str
    completed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class VerificationFailed:
    session_id: UUID
    step_id: str
    failure_output: str
    failed_at: datetime = field(default_factory=datetime.utcnow)
