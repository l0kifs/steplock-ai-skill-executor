"""End-to-end tests for the StepLock MCP server.

Tests use the FastMCP in-memory client transport to interact with the server
directly without subprocess or network overhead. Skill paths are registered via
InMemorySkillRegistry so the agent never has access to filesystem paths.
"""

from __future__ import annotations

import pytest
from fastmcp import Client

import steplock.entry_points.mcp.server as _server_module
from steplock.entry_points.mcp.server import create_server
from steplock.infrastructure.skill.registry import (
    CompositeSkillRegistry,
    InMemorySkillRegistry,
    SkillsRegistry,
)
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_server(*skill_paths: str):
    """Return a fresh server with the given paths registered."""
    return create_server(skill_registry=InMemorySkillRegistry(list(skill_paths)))


def make_composite_server(*path_groups: list[str]):
    """Return a server backed by a CompositeSkillRegistry merging N InMemorySkillRegistries."""
    registries = [InMemorySkillRegistry(paths) for paths in path_groups]
    return create_server(skill_registry=CompositeSkillRegistry(registries))


# ---------------------------------------------------------------------------
# Skill fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_skill(tmp_path):
    """Two-step skill with no verification."""
    skill_dir = tmp_path / "simple-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.yaml").write_text(
        """
name: simple-skill
description: A simple two-step skill with no verification.

steps:
  - id: step-1
    instruction: Do the first thing.

  - id: step-2
    instruction: Do the second thing.
""".strip()
    )
    return str(skill_dir)


@pytest.fixture
def file_instruction_skill(tmp_path):
    """Skill where instructions are loaded from markdown files."""
    skill_dir = tmp_path / "file-instruction-skill"
    skill_dir.mkdir()
    steps_dir = skill_dir / "steps"
    steps_dir.mkdir()
    (steps_dir / "step1.md").write_text("# Step 1\nComplete the first task.")
    (steps_dir / "step2.md").write_text("# Step 2\nComplete the second task.")

    (skill_dir / "SKILL.yaml").write_text(
        """
name: file-instruction-skill
description: Skill with file-based step instructions.

steps:
  - id: step-1
    instruction: steps/step1.md

  - id: step-2
    instruction: steps/step2.md
""".strip()
    )
    return str(skill_dir)


@pytest.fixture
def verify_pass_skill(tmp_path):
    """Two-step skill whose first step has a verification script that always passes."""
    skill_dir = tmp_path / "verify-pass-skill"
    skill_dir.mkdir()
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "verify.py").write_text("import sys\nsys.exit(0)\n")

    (skill_dir / "SKILL.yaml").write_text(
        """
name: verify-pass-skill
description: Skill whose verification always passes.

steps:
  - id: step-1
    instruction: Do something — verification will pass.
    verify: scripts/verify.py
    on_fail: retry

  - id: step-2
    instruction: Final step after verification passed.
""".strip()
    )
    return str(skill_dir)


@pytest.fixture
def verify_fail_retry_skill(tmp_path):
    """Single-step skill whose verification always fails with on_fail=retry."""
    skill_dir = tmp_path / "verify-fail-retry-skill"
    skill_dir.mkdir()
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "verify.py").write_text('import sys\nprint("Output must contain the word DONE")\nsys.exit(1)\n')

    (skill_dir / "SKILL.yaml").write_text(
        """
name: verify-fail-retry-skill
description: Skill whose verification always fails and retries.

steps:
  - id: step-1
    instruction: Produce output containing the word DONE.
    verify: scripts/verify.py
    on_fail: retry
""".strip()
    )
    return str(skill_dir)


@pytest.fixture
def verify_fail_abort_skill(tmp_path):
    """Single-step skill whose verification always fails with on_fail=abort."""
    skill_dir = tmp_path / "verify-fail-abort-skill"
    skill_dir.mkdir()
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "verify.py").write_text(
        'import sys\nprint("Verification failed: aborting execution")\nsys.exit(1)\n'
    )

    (skill_dir / "SKILL.yaml").write_text(
        """
name: verify-fail-abort-skill
description: Skill whose verification always fails and aborts.

steps:
  - id: step-1
    instruction: Attempt the task — it will always be aborted.
    verify: scripts/verify.py
    on_fail: abort
""".strip()
    )
    return str(skill_dir)


@pytest.fixture
def single_step_no_verify_skill(tmp_path):
    """Single-step skill with no verification — backwards-compatible Anthropic model."""
    skill_dir = tmp_path / "single-step-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.yaml").write_text(
        """
name: single-step-skill
description: Behaves identically to the Anthropic model skill.

steps:
  - id: step-1
    instruction: Do the only thing.
""".strip()
    )
    return str(skill_dir)


# ---------------------------------------------------------------------------
# Tests: list_skills
# ---------------------------------------------------------------------------


async def test_list_skills_returns_all_registered_skills(simple_skill, file_instruction_skill):
    server = make_server(simple_skill, file_instruction_skill)
    async with Client(server) as client:
        result = await client.call_tool("list_skills", {})
        skills = result.data

    names = {s["name"] for s in skills}
    assert names == {"simple-skill", "file-instruction-skill"}


async def test_list_skills_includes_descriptions(simple_skill):
    server = make_server(simple_skill)
    async with Client(server) as client:
        result = await client.call_tool("list_skills", {})
        skills = result.data

    assert skills[0]["description"] == "A simple two-step skill with no verification."


async def test_list_skills_returns_empty_when_registry_is_empty():
    server = make_server()  # no skills registered
    async with Client(server) as client:
        result = await client.call_tool("list_skills", {})
        skills = result.data

    assert skills == []


async def test_server_exposes_three_tools(simple_skill):
    server = make_server(simple_skill)
    async with Client(server) as client:
        tools = await client.list_tools()

    tool_names = {t.name for t in tools}
    assert tool_names == {"list_skills", "start_skill", "submit_step_output", "run_helper_script"}


# ---------------------------------------------------------------------------
# Tests: start_skill
# ---------------------------------------------------------------------------


async def test_start_skill_returns_first_step(simple_skill):
    server = make_server(simple_skill)
    async with Client(server) as client:
        result = await client.call_tool("start_skill", {"skill_name": "simple-skill"})
        data = result.data

    assert data["step_id"] == "step-1"
    assert data["instruction"] == "Do the first thing."
    assert data["session_id"]


async def test_start_skill_loads_file_instructions(file_instruction_skill):
    server = make_server(file_instruction_skill)
    async with Client(server) as client:
        result = await client.call_tool("start_skill", {"skill_name": "file-instruction-skill"})
        data = result.data

    assert data["step_id"] == "step-1"
    assert "Step 1" in data["instruction"]
    assert "Complete the first task." in data["instruction"]


async def test_start_skill_returns_error_for_unknown_name(simple_skill):
    server = make_server(simple_skill)
    async with Client(server) as client:
        result = await client.call_tool("start_skill", {"skill_name": "no-such-skill"})
        data = result.data

    assert "error" in data


async def test_start_skill_returns_error_when_registry_is_empty():
    server = make_server()
    async with Client(server) as client:
        result = await client.call_tool("start_skill", {"skill_name": "anything"})
        data = result.data

    assert "error" in data


# ---------------------------------------------------------------------------
# Tests: submit_step_output — no verification
# ---------------------------------------------------------------------------


async def test_submit_advances_to_next_step(simple_skill):
    server = make_server(simple_skill)
    async with Client(server) as client:
        start = await client.call_tool("start_skill", {"skill_name": "simple-skill"})
        session_id = start.data["session_id"]

        result = await client.call_tool(
            "submit_step_output",
            {"session_id": session_id, "output": "step 1 output"},
        )
        data = result.data

    assert data["status"] == "next_step"
    assert data["step_id"] == "step-2"
    assert data["instruction"] == "Do the second thing."


async def test_submit_completes_skill_on_last_step(simple_skill):
    server = make_server(simple_skill)
    async with Client(server) as client:
        start = await client.call_tool("start_skill", {"skill_name": "simple-skill"})
        session_id = start.data["session_id"]

        await client.call_tool("submit_step_output", {"session_id": session_id, "output": "step 1 done"})
        result = await client.call_tool("submit_step_output", {"session_id": session_id, "output": "step 2 done"})
        data = result.data

    assert data["status"] == "completed"


async def test_single_step_skill_completes_immediately(single_step_no_verify_skill):
    server = make_server(single_step_no_verify_skill)
    async with Client(server) as client:
        start = await client.call_tool("start_skill", {"skill_name": "single-step-skill"})
        session_id = start.data["session_id"]

        result = await client.call_tool("submit_step_output", {"session_id": session_id, "output": "done"})
        data = result.data

    assert data["status"] == "completed"


async def test_submit_returns_error_for_unknown_session(simple_skill):
    server = make_server(simple_skill)
    async with Client(server) as client:
        result = await client.call_tool(
            "submit_step_output",
            {"session_id": "00000000-0000-0000-0000-000000000000", "output": "anything"},
        )
        data = result.data

    assert "error" in data


async def test_submit_returns_error_for_invalid_session_id(simple_skill):
    server = make_server(simple_skill)
    async with Client(server) as client:
        result = await client.call_tool(
            "submit_step_output",
            {"session_id": "not-a-uuid", "output": "anything"},
        )
        data = result.data

    assert "error" in data


# ---------------------------------------------------------------------------
# Tests: submit_step_output — with verification
# ---------------------------------------------------------------------------


async def test_verification_passes_and_advances(verify_pass_skill):
    server = make_server(verify_pass_skill)
    async with Client(server) as client:
        start = await client.call_tool("start_skill", {"skill_name": "verify-pass-skill"})
        session_id = start.data["session_id"]

        result = await client.call_tool(
            "submit_step_output",
            {"session_id": session_id, "output": "any output — verify script always passes"},
        )
        data = result.data

    assert data["status"] == "next_step"
    assert data["step_id"] == "step-2"
    assert "instruction" in data


async def test_verification_fail_retry_resends_step_with_guidance(verify_fail_retry_skill):
    server = make_server(verify_fail_retry_skill)
    async with Client(server) as client:
        start = await client.call_tool("start_skill", {"skill_name": "verify-fail-retry-skill"})
        session_id = start.data["session_id"]

        result = await client.call_tool(
            "submit_step_output",
            {"session_id": session_id, "output": "output without the magic word"},
        )
        data = result.data

    assert data["status"] == "retry"
    assert data["step_id"] == "step-1"
    assert "instruction" in data
    assert data["message"]


async def test_verification_fail_retry_allows_second_attempt(verify_fail_retry_skill):
    server = make_server(verify_fail_retry_skill)
    async with Client(server) as client:
        start = await client.call_tool("start_skill", {"skill_name": "verify-fail-retry-skill"})
        session_id = start.data["session_id"]

        first = await client.call_tool("submit_step_output", {"session_id": session_id, "output": "wrong"})
        assert first.data["status"] == "retry"

        second = await client.call_tool("submit_step_output", {"session_id": session_id, "output": "still wrong"})
        assert second.data["status"] == "retry"


async def test_verification_fail_abort_halts_execution(verify_fail_abort_skill):
    server = make_server(verify_fail_abort_skill)
    async with Client(server) as client:
        start = await client.call_tool("start_skill", {"skill_name": "verify-fail-abort-skill"})
        session_id = start.data["session_id"]

        result = await client.call_tool("submit_step_output", {"session_id": session_id, "output": "any output"})
        data = result.data

    assert data["status"] == "aborted"
    assert data["message"]


async def test_aborted_session_rejects_further_submissions(verify_fail_abort_skill):
    server = make_server(verify_fail_abort_skill)
    async with Client(server) as client:
        start = await client.call_tool("start_skill", {"skill_name": "verify-fail-abort-skill"})
        session_id = start.data["session_id"]

        await client.call_tool("submit_step_output", {"session_id": session_id, "output": "first attempt"})
        result = await client.call_tool(
            "submit_step_output", {"session_id": session_id, "output": "second attempt after abort"}
        )
        data = result.data

    assert "error" in data


# ---------------------------------------------------------------------------
# Tests: multiple independent sessions
# ---------------------------------------------------------------------------


async def test_multiple_sessions_are_independent(simple_skill):
    """Two concurrent sessions must not interfere with each other."""
    server = make_server(simple_skill)
    async with Client(server) as client:
        start_a = await client.call_tool("start_skill", {"skill_name": "simple-skill"})
        start_b = await client.call_tool("start_skill", {"skill_name": "simple-skill"})
        session_a = start_a.data["session_id"]
        session_b = start_b.data["session_id"]

        assert session_a != session_b

        result_a = await client.call_tool("submit_step_output", {"session_id": session_a, "output": "a done"})
        result_b = await client.call_tool("submit_step_output", {"session_id": session_b, "output": "b done"})

    assert result_a.data["status"] == "next_step"
    assert result_a.data["step_id"] == "step-2"
    assert result_b.data["status"] == "next_step"
    assert result_b.data["step_id"] == "step-2"


# ---------------------------------------------------------------------------
# Tests: CompositeSkillRegistry
# ---------------------------------------------------------------------------


async def test_composite_registry_lists_skills_from_both_registries(simple_skill, single_step_no_verify_skill):
    server = make_composite_server([simple_skill], [single_step_no_verify_skill])
    async with Client(server) as client:
        result = await client.call_tool("list_skills", {})

    names = {s["name"] for s in result.data}
    assert names == {"simple-skill", "single-step-skill"}


async def test_composite_registry_can_start_skill_from_second_registry(simple_skill, single_step_no_verify_skill):
    server = make_composite_server([simple_skill], [single_step_no_verify_skill])
    async with Client(server) as client:
        result = await client.call_tool("start_skill", {"skill_name": "single-step-skill"})
        data = result.data

    assert data["step_id"] == "step-1"
    assert "session_id" in data


async def test_composite_registry_with_all_empty_registries():
    server = make_composite_server([], [])
    async with Client(server) as client:
        result = await client.call_tool("list_skills", {})

    assert result.data == []


async def test_composite_registry_one_empty_one_populated(simple_skill):
    server = make_composite_server([], [simple_skill])
    async with Client(server) as client:
        result = await client.call_tool("list_skills", {})

    names = {s["name"] for s in result.data}
    assert names == {"simple-skill"}


async def test_composite_registry_skills_from_both_registries_are_startable(simple_skill, file_instruction_skill):
    server = make_composite_server([simple_skill], [file_instruction_skill])
    async with Client(server) as client:
        result_a = await client.call_tool("start_skill", {"skill_name": "simple-skill"})
        result_b = await client.call_tool("start_skill", {"skill_name": "file-instruction-skill"})

    assert result_a.data["step_id"] == "step-1"
    assert result_b.data["step_id"] == "step-1"


# ---------------------------------------------------------------------------
# Tests: create_server default wiring — project registry detection
# ---------------------------------------------------------------------------


async def test_default_wiring_includes_project_registry_when_exists(monkeypatch, tmp_path, simple_skill):
    """When .steplock/skills-registry.yaml exists in the project dir, its skills are listed."""
    project_steplock = tmp_path / ".steplock"
    project_steplock.mkdir()
    project_registry = project_steplock / "skills-registry.yaml"
    project_registry.write_text(f"skills:\n  - {simple_skill}\n")

    home_registry = tmp_path / "home" / ".steplock" / "skills-registry.yaml"

    monkeypatch.setattr(_server_module, "SKILLS_REGISTRY_PATH", home_registry)
    monkeypatch.setattr(_server_module, "PROJECT_SKILLS_REGISTRY_PATH", project_registry)

    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("list_skills", {})

    names = {s["name"] for s in result.data}
    assert "simple-skill" in names


async def test_default_wiring_excludes_project_registry_when_not_exists(monkeypatch, tmp_path):
    """When project registry file does not exist, create_server raises no error and returns empty skills."""
    home_registry = tmp_path / "home" / ".steplock" / "skills-registry.yaml"
    nonexistent_project_registry = tmp_path / "project" / ".steplock" / "skills-registry.yaml"

    monkeypatch.setattr(_server_module, "SKILLS_REGISTRY_PATH", home_registry)
    monkeypatch.setattr(_server_module, "PROJECT_SKILLS_REGISTRY_PATH", nonexistent_project_registry)

    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("list_skills", {})

    assert result.data == []


async def test_default_wiring_does_not_create_project_registry(monkeypatch, tmp_path):
    """Project .steplock dir and registry file are never auto-created."""
    home_registry = tmp_path / "home" / ".steplock" / "skills-registry.yaml"
    project_steplock_dir = tmp_path / "project" / ".steplock"
    nonexistent_project_registry = project_steplock_dir / "skills-registry.yaml"

    monkeypatch.setattr(_server_module, "SKILLS_REGISTRY_PATH", home_registry)
    monkeypatch.setattr(_server_module, "PROJECT_SKILLS_REGISTRY_PATH", nonexistent_project_registry)

    create_server()

    assert not project_steplock_dir.exists()
    assert not nonexistent_project_registry.exists()


async def test_default_wiring_home_registry_auto_created(monkeypatch, tmp_path):
    """Home-dir registry is still auto-created on first use (existing behaviour preserved)."""
    home_registry = tmp_path / "home" / ".steplock" / "skills-registry.yaml"
    nonexistent_project_registry = tmp_path / "project" / ".steplock" / "skills-registry.yaml"

    monkeypatch.setattr(_server_module, "SKILLS_REGISTRY_PATH", home_registry)
    monkeypatch.setattr(_server_module, "PROJECT_SKILLS_REGISTRY_PATH", nonexistent_project_registry)

    server = create_server()
    async with Client(server) as client:
        await client.call_tool("list_skills", {})

    assert home_registry.exists()


async def test_default_wiring_merges_home_and_project_skills(
    monkeypatch, tmp_path, simple_skill, single_step_no_verify_skill
):
    """Skills from home-dir and project registries are both listed when both exist."""
    home_steplock = tmp_path / "home" / ".steplock"
    home_steplock.mkdir(parents=True)
    home_registry = home_steplock / "skills-registry.yaml"
    home_registry.write_text(f"skills:\n  - {simple_skill}\n")

    project_steplock = tmp_path / "project" / ".steplock"
    project_steplock.mkdir(parents=True)
    project_registry = project_steplock / "skills-registry.yaml"
    project_registry.write_text(f"skills:\n  - {single_step_no_verify_skill}\n")

    monkeypatch.setattr(_server_module, "SKILLS_REGISTRY_PATH", home_registry)
    monkeypatch.setattr(_server_module, "PROJECT_SKILLS_REGISTRY_PATH", project_registry)

    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("list_skills", {})

    names = {s["name"] for s in result.data}
    assert names == {"simple-skill", "single-step-skill"}


# ---------------------------------------------------------------------------
# Tests: helper scripts
# ---------------------------------------------------------------------------


@pytest.fixture
def helper_skill(tmp_path):
    """Skill with a helper script on the first step."""
    skill_dir = tmp_path / "helper-skill"
    skill_dir.mkdir()
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir()
    # Helper that echoes its arguments to stdout
    (scripts_dir / "get_info.py").write_text("import sys\nprint('info:' + ' '.join(sys.argv[1:]))\n")
    (skill_dir / "SKILL.yaml").write_text(
        """
name: helper-skill
description: Skill with a helper script.

steps:
  - id: step-1
    instruction: Use the helper to gather info.
    helpers:
      - scripts/get_info.py

  - id: step-2
    instruction: Finish up.
""".strip()
    )
    return str(skill_dir)


@pytest.fixture
def helper_stderr_skill(tmp_path):
    """Skill with a helper that writes to stderr and exits non-zero."""
    skill_dir = tmp_path / "helper-stderr-skill"
    skill_dir.mkdir()
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "failing_helper.py").write_text("import sys\nsys.stderr.write('error detail\\n')\nsys.exit(2)\n")
    (skill_dir / "SKILL.yaml").write_text(
        """
name: helper-stderr-skill
description: Skill with a helper that exits non-zero.

steps:
  - id: step-1
    instruction: Run the failing helper.
    helpers:
      - scripts/failing_helper.py
""".strip()
    )
    return str(skill_dir)


async def test_server_exposes_four_tools(simple_skill):
    server = make_server(simple_skill)
    async with Client(server) as client:
        tools = await client.list_tools()

    tool_names = {t.name for t in tools}
    assert tool_names == {"list_skills", "start_skill", "submit_step_output", "run_helper_script"}


async def test_start_skill_includes_helper_scripts(helper_skill):
    server = make_server(helper_skill)
    async with Client(server) as client:
        result = await client.call_tool("start_skill", {"skill_name": "helper-skill"})
        data = result.data

    assert data["helper_scripts"] == ["get_info"]


async def test_start_skill_no_helpers_returns_empty_list(simple_skill):
    server = make_server(simple_skill)
    async with Client(server) as client:
        result = await client.call_tool("start_skill", {"skill_name": "simple-skill"})
        data = result.data

    assert data["helper_scripts"] == []


async def test_submit_step_output_next_step_includes_helper_scripts(helper_skill):
    """helper_scripts for the next step are returned when advancing."""
    server = make_server(helper_skill)
    async with Client(server) as client:
        start = await client.call_tool("start_skill", {"skill_name": "helper-skill"})
        session_id = start.data["session_id"]

        result = await client.call_tool("submit_step_output", {"session_id": session_id, "output": "done"})
        data = result.data

    assert data["status"] == "next_step"
    assert data.get("helper_scripts", []) == []


async def test_run_helper_script_returns_stdout(helper_skill):
    server = make_server(helper_skill)
    async with Client(server) as client:
        start = await client.call_tool("start_skill", {"skill_name": "helper-skill"})
        session_id = start.data["session_id"]

        result = await client.call_tool(
            "run_helper_script",
            {"session_id": session_id, "script_name": "get_info"},
        )
        data = result.data

    assert data["exit_code"] == 0
    assert "info:" in data["stdout"]
    assert data["stderr"] == ""


async def test_run_helper_script_passes_args(helper_skill):
    server = make_server(helper_skill)
    async with Client(server) as client:
        start = await client.call_tool("start_skill", {"skill_name": "helper-skill"})
        session_id = start.data["session_id"]

        result = await client.call_tool(
            "run_helper_script",
            {"session_id": session_id, "script_name": "get_info", "args": ["foo", "bar"]},
        )
        data = result.data

    assert data["exit_code"] == 0
    assert "info:foo bar" in data["stdout"]


async def test_run_helper_script_returns_stderr_and_exit_code(helper_stderr_skill):
    server = make_server(helper_stderr_skill)
    async with Client(server) as client:
        start = await client.call_tool("start_skill", {"skill_name": "helper-stderr-skill"})
        session_id = start.data["session_id"]

        result = await client.call_tool(
            "run_helper_script",
            {"session_id": session_id, "script_name": "failing_helper"},
        )
        data = result.data

    assert data["exit_code"] == 2
    assert "error detail" in data["stderr"]


async def test_run_helper_script_unknown_name_returns_error(helper_skill):
    server = make_server(helper_skill)
    async with Client(server) as client:
        start = await client.call_tool("start_skill", {"skill_name": "helper-skill"})
        session_id = start.data["session_id"]

        result = await client.call_tool(
            "run_helper_script",
            {"session_id": session_id, "script_name": "no_such_helper"},
        )
        data = result.data

    assert "error" in data


async def test_run_helper_script_invalid_session_returns_error(helper_skill):
    server = make_server(helper_skill)
    async with Client(server) as client:
        result = await client.call_tool(
            "run_helper_script",
            {"session_id": "00000000-0000-0000-0000-000000000000", "script_name": "get_info"},
        )
        data = result.data

    assert "error" in data


async def test_run_helper_script_not_available_on_next_step(helper_skill):
    """After advancing, step-2 has no helpers — run_helper_script must fail."""
    server = make_server(helper_skill)
    async with Client(server) as client:
        start = await client.call_tool("start_skill", {"skill_name": "helper-skill"})
        session_id = start.data["session_id"]

        # Advance to step-2
        await client.call_tool("submit_step_output", {"session_id": session_id, "output": "done"})

        result = await client.call_tool(
            "run_helper_script",
            {"session_id": session_id, "script_name": "get_info"},
        )
        data = result.data

    assert "error" in data


# ---------------------------------------------------------------------------
# Tests: Auto-Discovery and Folder Support
# ---------------------------------------------------------------------------


@pytest.fixture
def steplock_dir(tmp_path):
    """Create a .steplock directory with skills for auto-discovery testing."""
    steplock = tmp_path / ".steplock"
    steplock.mkdir()

    # Create a skill directly in .steplock
    skill1 = steplock / "auto-skill-1"
    skill1.mkdir()
    (skill1 / "SKILL.yaml").write_text(
        """
name: auto-skill-1
description: Auto-discovered skill from .steplock root.

steps:
  - id: step-1
    instruction: Run auto-discovered skill step 1.
""".strip()
    )

    # Create a skill in a nested subdirectory
    nested = steplock / "sub" / "nested" / "auto-skill-2"
    nested.mkdir(parents=True)
    (nested / "SKILL.yaml").write_text(
        """
name: auto-skill-2
description: Auto-discovered skill from nested directory.

steps:
  - id: step-1
    instruction: Run nested auto-discovered skill step 1.
""".strip()
    )

    return str(steplock)


@pytest.fixture
def folder_with_skills(tmp_path):
    """Create a folder containing multiple skills for folder scanning tests."""
    folder = tmp_path / "skills-folder"
    folder.mkdir()

    # Create skill at root level
    skill1 = folder / "folder-skill-1"
    skill1.mkdir()
    (skill1 / "SKILL.yaml").write_text(
        """
name: folder-skill-1
description: Skill in folder root.

steps:
  - id: step-1
    instruction: Step 1 of folder skill 1.
""".strip()
    )

    # Create skill in subfolder
    skill2 = folder / "sub" / "folder-skill-2"
    skill2.mkdir(parents=True)
    (skill2 / "SKILL.yaml").write_text(
        """
name: folder-skill-2
description: Skill in subfolder.

steps:
  - id: step-1
    instruction: Step 1 of folder skill 2.
""".strip()
    )

    # Create skill in deep nested subfolder
    skill3 = folder / "sub" / "deep" / "folder-skill-3"
    skill3.mkdir(parents=True)
    (skill3 / "SKILL.yaml").write_text(
        """
name: folder-skill-3
description: Skill in deep nested folder.

steps:
  - id: step-1
    instruction: Step 1 of folder skill 3.
""".strip()
    )

    return str(folder)


@pytest.mark.e2e
async def test_auto_discovered_skills_available_in_server(steplock_dir, tmp_path):
    """Skills auto-discovered from .steplock directories are available."""
    # Arrange
    registry_path = tmp_path / "registry.yaml"
    registry = SkillsRegistry(registry_path, auto_discover_base=Path(steplock_dir))
    server = create_server(skill_registry=registry)

    # Act
    async with Client(server) as client:
        result = await client.call_tool("list_skills", {})
        skills = result.data

    # Assert
    names = {s["name"] for s in skills}
    assert "auto-skill-1" in names
    assert "auto-skill-2" in names


@pytest.mark.e2e
async def test_folder_in_registry_discovers_nested_skills(folder_with_skills, tmp_path):
    """Skill folders in registry discover nested skills."""
    # Arrange
    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text(f"skills:\n  - {folder_with_skills}\n")

    registry = SkillsRegistry(registry_path)
    server = create_server(skill_registry=registry)

    # Act
    async with Client(server) as client:
        result = await client.call_tool("list_skills", {})
        skills = result.data

    # Assert
    names = {s["name"] for s in skills}
    assert "folder-skill-1" in names
    assert "folder-skill-2" in names
    assert "folder-skill-3" in names


@pytest.mark.e2e
async def test_mixed_registry_entries_work_correctly(steplock_dir, folder_with_skills, tmp_path):
    """Mixed registry entries (individual paths + folders) work correctly."""
    # Arrange
    # Create an additional skill for explicit registry entry
    explicit_skill_dir = tmp_path / "explicit-skill"
    explicit_skill_dir.mkdir()
    (explicit_skill_dir / "SKILL.yaml").write_text(
        """
name: explicit-skill
description: Explicitly registered skill.

steps:
  - id: step-1
    instruction: Step 1 of explicit skill.
""".strip()
    )

    # Create registry with mixed entries
    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text(
        f"""skills:
  - {explicit_skill_dir}
  - {folder_with_skills}
"""
    )

    # Add auto-discovery from steplock_dir
    registry = SkillsRegistry(registry_path, auto_discover_base=Path(steplock_dir))
    server = create_server(skill_registry=registry)

    # Act
    async with Client(server) as client:
        result = await client.call_tool("list_skills", {})
        skills = result.data

    # Assert
    names = {s["name"] for s in skills}
    # Auto-discovered
    assert "auto-skill-1" in names
    assert "auto-skill-2" in names
    # From folder
    assert "folder-skill-1" in names
    assert "folder-skill-2" in names
    assert "folder-skill-3" in names
    # Explicit
    assert "explicit-skill" in names


@pytest.mark.e2e
async def test_composite_registry_precedence_project_local_wins(
    tmp_path,
):
    """Project-local skills take precedence over user-wide (same name)."""
    # Arrange
    # User-wide skill with name "priority-skill"
    user_skill_dir = tmp_path / "user" / "priority-skill"
    user_skill_dir.mkdir(parents=True)
    (user_skill_dir / "SKILL.yaml").write_text(
        """
name: priority-skill
description: User-wide skill with priority.

steps:
  - id: step-1
    instruction: User skill step.
""".strip()
    )

    # Project-local skill with same name
    project_skill_dir = tmp_path / "project" / "priority-skill"
    project_skill_dir.mkdir(parents=True)
    (project_skill_dir / "SKILL.yaml").write_text(
        """
name: priority-skill
description: Project-local skill that should win.

steps:
  - id: step-1
    instruction: Project skill step.
""".strip()
    )

    user_registry = InMemorySkillRegistry([str(user_skill_dir)])
    project_registry = InMemorySkillRegistry([str(project_skill_dir)])

    # User registry first, project registry second (should win)
    composite = CompositeSkillRegistry([user_registry, project_registry])
    server = create_server(skill_registry=composite)

    # Act
    async with Client(server) as client:
        result = await client.call_tool("list_skills", {})
        skills = result.data

    # Assert
    assert len(skills) == 1
    assert skills[0]["name"] == "priority-skill"
    # The project-local skill should be the one available
    # We can verify by checking the description
    assert "Project-local" in skills[0]["description"]


@pytest.mark.e2e
async def test_deduplication_same_path_appears_twice(folder_with_skills, tmp_path):
    """Same skill path appearing twice is deduplicated."""
    # Arrange
    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text(
        f"""skills:
  - {folder_with_skills}
  - {folder_with_skills}
"""
    )

    registry = SkillsRegistry(registry_path)
    server = create_server(skill_registry=registry)

    # Act
    async with Client(server) as client:
        result = await client.call_tool("list_skills", {})
        skills = result.data

    # Assert
    names = [s["name"] for s in skills]
    # No duplicates - each skill name appears once
    assert len(names) == len(set(names))
    assert "folder-skill-1" in names
    assert "folder-skill-2" in names
    assert "folder-skill-3" in names
