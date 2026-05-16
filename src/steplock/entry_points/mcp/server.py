"""FastMCP server — gatekeeper runtime for step-by-step AI skill execution."""

from __future__ import annotations

from fastmcp import FastMCP

from steplock.application.skill.commands import StartSkillCommand, SubmitStepOutputCommand
from steplock.application.skill.ports import ISkillRegistry
from steplock.application.skill.services import SkillExecutionService
from steplock.config.settings import SKILLS_REGISTRY_PATH
from steplock.domains.skill.exceptions import SessionNotFoundError, SkillNotFoundError
from steplock.infrastructure.skill.loaders import YamlSkillLoader
from steplock.infrastructure.skill.registry import SkillsRegistry
from steplock.infrastructure.skill.repositories import InMemorySessionRepository
from steplock.infrastructure.skill.runners import SubprocessVerificationRunner


def create_server(skill_registry: ISkillRegistry | None = None) -> FastMCP:
    """Wire dependencies and return a configured FastMCP server instance.

    Args:
        skill_registry: Override the default filesystem registry. Useful for testing.
    """
    if skill_registry is None:
        skill_registry = SkillsRegistry(SKILLS_REGISTRY_PATH)

    skill_loader = YamlSkillLoader()
    verification_runner = SubprocessVerificationRunner()
    session_repository = InMemorySessionRepository()

    service = SkillExecutionService(
        skill_loader=skill_loader,
        verification_runner=verification_runner,
        session_repository=session_repository,
        skill_registry=skill_registry,
    )

    mcp = FastMCP(
        "StepLock",
        instructions=(
            "A gatekeeper runtime that enforces step-by-step AI skill execution with output verification. "
            "Call list_skills to discover available skills. "
            "Call start_skill with a skill name to begin execution and receive the first step instruction. "
            "Call submit_step_output to submit your output for the current step and receive the next one."
        ),
    )

    @mcp.tool
    def list_skills() -> list[dict]:
        """List all skills available in the registry.

        Returns the name and description of each registered skill.
        Use a skill's name with start_skill to begin execution.
        """
        result = service.list_skills()
        return [{"name": s.name, "description": s.description} for s in result.skills]

    @mcp.tool
    def start_skill(skill_name: str) -> dict:
        """Start executing a skill by name. Returns the session_id and the first step instruction.

        Args:
            skill_name: Name of the skill as returned by list_skills.
        """
        try:
            result = service.start_skill(StartSkillCommand(skill_name=skill_name))
        except SkillNotFoundError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": str(e)}

        return {
            "session_id": result.session_id,
            "step_id": result.step_id,
            "instruction": result.instruction,
        }

    @mcp.tool
    def submit_step_output(session_id: str, output: str) -> dict:
        """Submit your output for the current step.

        The server verifies the output (if a verify script is configured) and returns either
        the next step, a retry request with guidance, an abort notice, or a completion signal.

        Args:
            session_id: The session identifier returned by start_skill.
            output: The output produced while executing the current step instruction.
        """
        try:
            result = service.submit_step_output(SubmitStepOutputCommand(session_id=session_id, output=output))
        except SessionNotFoundError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": str(e)}

        response: dict = {"status": result.status}
        if result.step_id is not None:
            response["step_id"] = result.step_id
        if result.instruction is not None:
            response["instruction"] = result.instruction
        if result.message is not None:
            response["message"] = result.message
        return response

    return mcp


mcp = create_server()

if __name__ == "__main__":
    mcp.run()
