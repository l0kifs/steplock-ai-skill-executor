"""FastMCP server — gatekeeper runtime for step-by-step AI skill execution."""

from __future__ import annotations

from fastmcp import FastMCP

from steplock.application.skill.commands import RunHelperScriptCommand, StartSkillCommand, SubmitStepOutputCommand
from steplock.application.skill.ports import ISkillRegistry
from steplock.application.skill.services import SkillExecutionService
from steplock.config.settings import PROJECT_SKILLS_REGISTRY_PATH, SKILLS_REGISTRY_PATH
from steplock.domains.skill.exceptions import SessionNotFoundError, SkillNotFoundError
from steplock.infrastructure.skill.loaders import YamlSkillLoader
from steplock.infrastructure.skill.registry import CompositeSkillRegistry, SkillsRegistry
from steplock.infrastructure.skill.repositories import InMemorySessionRepository
from steplock.infrastructure.skill.runners import SubprocessHelperRunner, SubprocessVerificationRunner


def create_server(skill_registry: ISkillRegistry | None = None) -> FastMCP:
    """Wire dependencies and return a configured FastMCP server instance.

    Args:
        skill_registry: Override the default filesystem registry. Useful for testing.
    """
    if skill_registry is None:
        registries: list[ISkillRegistry] = [SkillsRegistry(SKILLS_REGISTRY_PATH)]
        if PROJECT_SKILLS_REGISTRY_PATH.exists():
            registries.append(SkillsRegistry(PROJECT_SKILLS_REGISTRY_PATH))
        skill_registry = CompositeSkillRegistry(registries)

    skill_loader = YamlSkillLoader()
    verification_runner = SubprocessVerificationRunner()
    helper_runner = SubprocessHelperRunner()
    session_repository = InMemorySessionRepository()

    service = SkillExecutionService(
        skill_loader=skill_loader,
        verification_runner=verification_runner,
        session_repository=session_repository,
        skill_registry=skill_registry,
        helper_runner=helper_runner,
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
            "helper_scripts": result.helper_scripts,
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
        if result.helper_scripts:
            response["helper_scripts"] = result.helper_scripts
        return response

    @mcp.tool
    def run_helper_script(session_id: str, script_name: str, args: list[str] | None = None) -> dict:
        """Run a helper script available on the current step.

        Helper scripts provide utility actions the agent can invoke during a step,
        such as gathering context or performing preparatory work.

        Args:
            session_id: The session identifier returned by start_skill.
            script_name: Name of the helper script as listed in helper_scripts.
            args: Optional list of string arguments passed to the script via sys.argv.
        """
        try:
            result = service.run_helper_script(
                RunHelperScriptCommand(
                    session_id=session_id,
                    script_name=script_name,
                    args=args or [],
                )
            )
        except (SessionNotFoundError, ValueError) as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": str(e)}

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
        }

    return mcp


mcp = create_server()

if __name__ == "__main__":
    mcp.run(show_banner=False)
