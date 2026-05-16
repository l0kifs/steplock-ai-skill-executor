"""Skill application use cases."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

from steplock.application.skill.commands import RunHelperScriptCommand, StartSkillCommand, SubmitStepOutputCommand
from steplock.application.skill.ports import (
    IHelperRunner,
    ISessionRepository,
    ISkillLoader,
    ISkillRegistry,
    IVerificationRunner,
)
from steplock.domains.skill.exceptions import SessionNotFoundError, SkillNotFoundError
from steplock.domains.skill.models import SkillSession


@dataclass
class SkillInfo:
    name: str
    description: str


@dataclass
class ListSkillsResult:
    skills: list[SkillInfo] = field(default_factory=list)


@dataclass
class StartSkillResult:
    session_id: str
    step_id: str
    instruction: str
    helper_scripts: list[str] = field(default_factory=list)


@dataclass
class SubmitStepResult:
    status: Literal["next_step", "completed", "retry", "aborted"]
    step_id: str | None = None
    instruction: str | None = None
    message: str | None = None
    helper_scripts: list[str] = field(default_factory=list)


@dataclass
class RunHelperScriptResult:
    stdout: str
    stderr: str
    exit_code: int


class SkillExecutionService:
    def __init__(
        self,
        skill_loader: ISkillLoader,
        verification_runner: IVerificationRunner,
        session_repository: ISessionRepository,
        skill_registry: ISkillRegistry,
        helper_runner: IHelperRunner,
    ) -> None:
        self._skill_loader = skill_loader
        self._verification_runner = verification_runner
        self._session_repository = session_repository
        self._skill_registry = skill_registry
        self._helper_runner = helper_runner

    def list_skills(self) -> ListSkillsResult:
        """Return name and description for every skill in the registry."""
        paths = self._skill_registry.list_skill_paths()
        skills: list[SkillInfo] = []
        for path in paths:
            try:
                skill = self._skill_loader.load(path)
                skills.append(SkillInfo(name=skill.name, description=skill.description))
            except Exception:
                pass
        return ListSkillsResult(skills=skills)

    def start_skill(self, command: StartSkillCommand) -> StartSkillResult:
        paths = self._skill_registry.list_skill_paths()
        for path in paths:
            try:
                skill = self._skill_loader.load(path)
            except Exception:
                continue
            if skill.name == command.skill_name:
                if not skill.steps:
                    raise ValueError(f"Skill '{skill.name}' has no steps defined")
                session = SkillSession(skill=skill)
                self._session_repository.save(session)
                step = session.get_current_step()
                return StartSkillResult(
                    session_id=str(session.session_id),
                    step_id=step.id,
                    instruction=step.instruction,
                    helper_scripts=list(step.helper_script_paths.keys()),
                )
        raise SkillNotFoundError(command.skill_name)

    def submit_step_output(self, command: SubmitStepOutputCommand) -> SubmitStepResult:
        try:
            session_uuid = UUID(command.session_id)
        except ValueError:
            raise SessionNotFoundError(command.session_id)

        session = self._session_repository.find_by_id(session_uuid)
        if session is None:
            raise SessionNotFoundError(command.session_id)

        step = session.get_current_step()
        if step is None:
            raise ValueError(f"Session '{command.session_id}' has no active step (status: {session.status})")

        if step.verify_script_path is not None:
            passed, script_output = self._verification_runner.run(
                script_path=step.verify_script_path,
                output=command.output,
            )
            if not passed:
                if step.on_fail == "abort":
                    session.abort()
                    self._session_repository.save(session)
                    return SubmitStepResult(status="aborted", message=script_output)
                else:
                    return SubmitStepResult(
                        status="retry",
                        step_id=step.id,
                        instruction=step.instruction,
                        message=script_output,
                        helper_scripts=list(step.helper_script_paths.keys()),
                    )

        has_more = session.advance()
        self._session_repository.save(session)

        if not has_more:
            return SubmitStepResult(status="completed")

        next_step = session.get_current_step()
        return SubmitStepResult(
            status="next_step",
            step_id=next_step.id,
            instruction=next_step.instruction,
            helper_scripts=list(next_step.helper_script_paths.keys()),
        )

    def run_helper_script(self, command: RunHelperScriptCommand) -> RunHelperScriptResult:
        try:
            session_uuid = UUID(command.session_id)
        except ValueError:
            raise SessionNotFoundError(command.session_id)

        session = self._session_repository.find_by_id(session_uuid)
        if session is None:
            raise SessionNotFoundError(command.session_id)

        step = session.get_current_step()
        if step is None:
            raise ValueError(f"Session '{command.session_id}' has no active step (status: {session.status})")

        script_path = step.helper_script_paths.get(command.script_name)
        if script_path is None:
            available = ", ".join(step.helper_script_paths.keys()) or "none"
            raise ValueError(
                f"Helper script '{command.script_name}' not found on current step '{step.id}'. "
                f"Available helpers: {available}"
            )

        stdout, stderr, exit_code = self._helper_runner.run(
            script_path=script_path,
            args=command.args,
        )
        return RunHelperScriptResult(stdout=stdout, stderr=stderr, exit_code=exit_code)
