"""End-to-end tests for the StepLock MCP server.

Tests use the FastMCP in-memory client transport to interact with the server
directly without subprocess or network overhead. Skill paths are registered via
InMemorySkillRegistry so the agent never has access to filesystem paths.
"""

from __future__ import annotations

import pytest
from fastmcp import Client

from steplock.entry_points.mcp.server import create_server
from steplock.infrastructure.skill.registry import InMemorySkillRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_server(*skill_paths: str):
    """Return a fresh server with the given paths registered."""
    return create_server(skill_registry=InMemorySkillRegistry(list(skill_paths)))


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
    (scripts_dir / "verify.py").write_text(
        'import sys\nprint("Output must contain the word DONE")\nsys.exit(1)\n'
    )

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
    assert tool_names == {"list_skills", "start_skill", "submit_step_output"}


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

