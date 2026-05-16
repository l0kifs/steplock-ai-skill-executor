"""In-memory skill session repository."""

from __future__ import annotations

from uuid import UUID

from steplock.application.skill.ports import ISessionRepository
from steplock.domains.skill.models import SkillSession


class InMemorySessionRepository(ISessionRepository):
    def __init__(self) -> None:
        self._sessions: dict[UUID, SkillSession] = {}

    def save(self, session: SkillSession) -> None:
        self._sessions[session.session_id] = session

    def find_by_id(self, session_id: UUID) -> SkillSession | None:
        return self._sessions.get(session_id)

    def delete(self, session_id: UUID) -> None:
        self._sessions.pop(session_id, None)
