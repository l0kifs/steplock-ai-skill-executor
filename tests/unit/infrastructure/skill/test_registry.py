"""Unit tests for skill registry implementations."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

from steplock.infrastructure.skill.registry import (
    CompositeSkillRegistry,
    InMemorySkillRegistry,
    SkillsRegistry,
    _discover_skills_in_directory,
    _resolve_registry_paths,
)


# ---------------------------------------------------------------------------
# Helper Functions Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDiscoverSkillsInDirectory:
    """Tests for _discover_skills_in_directory function."""

    def test_discovers_skill_in_directory(self, tmp_path, caplog):
        """Auto-discover skill from directory with SKILL.yaml."""
        # Arrange
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.yaml").write_text("name: my-skill\n")
        visited: set[str] = set()

        # Act
        with caplog.at_level(logging.WARNING):
            result = _discover_skills_in_directory(tmp_path, visited)

        # Assert
        assert len(result) == 1
        assert result[0] == str(skill_dir.resolve())

    def test_discovers_nested_skill(self, tmp_path, caplog):
        """Auto-discover skill from nested subdirectory."""
        # Arrange
        nested_skill = tmp_path / "sub" / "deep" / "my-skill"
        nested_skill.mkdir(parents=True)
        (nested_skill / "SKILL.yaml").write_text("name: nested-skill\n")
        visited: set[str] = set()

        # Act
        with caplog.at_level(logging.WARNING):
            result = _discover_skills_in_directory(tmp_path, visited)

        # Assert
        assert len(result) == 1
        assert result[0] == str(nested_skill.resolve())

    def test_discovers_multiple_skills_recursively(self, tmp_path):
        """Discovers multiple skills at different nesting levels."""
        # Arrange
        skill1 = tmp_path / "skill1"
        skill1.mkdir()
        (skill1 / "SKILL.yaml").write_text("name: skill1\n")

        skill2 = tmp_path / "sub" / "skill2"
        skill2.mkdir(parents=True)
        (skill2 / "SKILL.yaml").write_text("name: skill2\n")

        skill3 = tmp_path / "sub" / "deep" / "skill3"
        skill3.mkdir(parents=True)
        (skill3 / "SKILL.yaml").write_text("name: skill3\n")

        visited: set[str] = set()

        # Act
        result = _discover_skills_in_directory(tmp_path, visited)

        # Assert
        assert len(result) == 3
        paths = [Path(p).name for p in result]
        assert "skill1" in paths
        assert "skill2" in paths
        assert "skill3" in paths

    def test_ignores_non_skill_directories(self, tmp_path):
        """Directories without SKILL.yaml are not returned."""
        # Arrange
        regular_dir = tmp_path / "regular-dir"
        regular_dir.mkdir()
        (regular_dir / "some-file.txt").write_text("not a skill")
        visited: set[str] = set()

        # Act
        result = _discover_skills_in_directory(tmp_path, visited)

        # Assert
        assert len(result) == 0

    def test_circular_symlink_detection(self, tmp_path, caplog):
        """Circular symlink references are detected and skipped."""
        # Arrange
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.yaml").write_text("name: circular-skill\n")

        # Create a symlink that points back to the parent
        symlink_dir = tmp_path / "symlink-dir"
        symlink_dir.symlink_to(tmp_path)

        visited: set[str] = set()

        # Act
        with caplog.at_level(logging.WARNING):
            result = _discover_skills_in_directory(tmp_path, visited)

        # Assert
        assert len(result) == 1  # Only the real skill, not infinite loop
        # Warning should be logged about skipping visited directory
        assert any("already-visited" in record.message or "cycle" in record.message
                   for record in caplog.records)

    def test_empty_directory_handling(self, tmp_path, caplog):
        """Empty directory returns empty list without errors."""
        # Arrange
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        visited: set[str] = set()

        # Act
        with caplog.at_level(logging.WARNING):
            result = _discover_skills_in_directory(empty_dir, visited)

        # Assert
        assert result == []

    def test_non_existent_directory(self, tmp_path):
        """Non-existent directory returns empty list."""
        # Arrange
        non_existent = tmp_path / "does-not-exist"
        visited: set[str] = set()

        # Act
        result = _discover_skills_in_directory(non_existent, visited)

        # Assert
        assert result == []


@pytest.mark.unit
class TestResolveRegistryPaths:
    """Tests for _resolve_registry_paths function."""

    def test_resolves_skill_directory_path(self, tmp_path):
        """Skill directory path is resolved correctly."""
        # Arrange
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.yaml").write_text("name: my-skill\n")

        # Act
        result = _resolve_registry_paths([str(skill_dir)])

        # Assert
        assert len(result) == 1
        assert result[0] == str(skill_dir.resolve())

    def test_expands_folder_to_skills(self, tmp_path):
        """Folder path in registry discovers nested skills."""
        # Arrange
        skill1 = tmp_path / "skill1"
        skill1.mkdir()
        (skill1 / "SKILL.yaml").write_text("name: skill1\n")

        skill2 = tmp_path / "sub" / "skill2"
        skill2.mkdir(parents=True)
        (skill2 / "SKILL.yaml").write_text("name: skill2\n")

        # Act
        result = _resolve_registry_paths([str(tmp_path)])

        # Assert
        assert len(result) == 2

    def test_handles_skill_yaml_file_in_registry(self, tmp_path):
        """SKILL.yaml file in registry uses its parent directory."""
        # Arrange
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.yaml").write_text("name: my-skill\n")
        skill_yaml_path = skill_dir / "SKILL.yaml"

        # Act
        result = _resolve_registry_paths([str(skill_yaml_path)])

        # Assert
        assert len(result) == 1
        assert result[0] == str(skill_dir.resolve())

    def test_handles_file_in_registry_not_directory(self, tmp_path, caplog):
        """Non-directory file in registry is skipped with warning."""
        # Arrange
        regular_file = tmp_path / "config.yaml"
        regular_file.write_text("key: value\n")

        # Act
        with caplog.at_level(logging.WARNING):
            result = _resolve_registry_paths([str(regular_file)])

        # Assert
        assert result == []
        assert any("not a directory" in record.message for record in caplog.records)

    def test_handles_non_existent_path(self, tmp_path, caplog):
        """Non-existent path in registry is skipped with warning."""
        # Arrange
        non_existent = str(tmp_path / "does-not-exist")

        # Act
        with caplog.at_level(logging.WARNING):
            result = _resolve_registry_paths([non_existent])

        # Assert
        assert result == []
        assert any("does not exist" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# SkillsRegistry Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSkillsRegistry:
    """Tests for SkillsRegistry class."""

    def test_list_skill_paths_returns_explicit_paths(self, tmp_path):
        """Registry returns paths listed in YAML file."""
        # Arrange
        registry_path = tmp_path / "registry.yaml"
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.yaml").write_text("name: my-skill\n")
        registry_path.write_text(f"skills:\n  - {skill_dir}\n")

        registry = SkillsRegistry(registry_path)

        # Act
        result = registry.list_skill_paths()

        # Assert
        assert len(result) == 1
        assert "my-skill" in result[0]

    def test_auto_discovers_skills(self, tmp_path):
        """Registry auto-discovers skills from base directory."""
        # Arrange
        registry_path = tmp_path / "registry.yaml"
        auto_discover_base = tmp_path / ".steplock"
        auto_discover_base.mkdir()

        skill_dir = auto_discover_base / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.yaml").write_text("name: my-skill\n")

        registry = SkillsRegistry(registry_path, auto_discover_base=auto_discover_base)

        # Act
        result = registry.list_skill_paths()

        # Assert
        assert len(result) == 1
        assert "my-skill" in result[0]

    def test_combines_auto_discovered_and_explicit(self, tmp_path):
        """Registry combines auto-discovered and explicit paths."""
        # Arrange
        registry_path = tmp_path / "registry.yaml"
        auto_discover_base = tmp_path / ".steplock"
        auto_discover_base.mkdir()

        # Auto-discovered skill
        auto_skill = auto_discover_base / "auto-skill"
        auto_skill.mkdir()
        (auto_skill / "SKILL.yaml").write_text("name: auto-skill\n")

        # Explicit path
        explicit_skill = tmp_path / "explicit-skill"
        explicit_skill.mkdir()
        (explicit_skill / "SKILL.yaml").write_text("name: explicit-skill\n")
        registry_path.write_text(f"skills:\n  - {explicit_skill}\n")

        registry = SkillsRegistry(registry_path, auto_discover_base=auto_discover_base)

        # Act
        result = registry.list_skill_paths()

        # Assert
        assert len(result) == 2
        paths_str = " ".join(result)
        assert "auto-skill" in paths_str
        assert "explicit-skill" in paths_str


# ---------------------------------------------------------------------------
# CompositeSkillRegistry Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCompositeSkillRegistry:
    """Tests for CompositeSkillRegistry class."""

    def test_merges_paths_from_multiple_registries(self):
        """Composite registry merges paths from all registries."""
        # Arrange
        registry1 = InMemorySkillRegistry(["/path/to/skill1"])
        registry2 = InMemorySkillRegistry(["/path/to/skill2"])
        composite = CompositeSkillRegistry([registry1, registry2])

        # Act
        result = composite.list_skill_paths()

        # Assert
        assert len(result) == 2
        assert "/path/to/skill1" in result
        assert "/path/to/skill2" in result

    def test_deduplication_by_path(self):
        """Same skill path appearing twice is deduplicated."""
        # Arrange
        registry1 = InMemorySkillRegistry(["/path/to/skill1", "/path/to/skill2"])
        registry2 = InMemorySkillRegistry(["/path/to/skill2", "/path/to/skill3"])
        composite = CompositeSkillRegistry([registry1, registry2])

        # Act
        result = composite.list_skill_paths()

        # Assert
        assert len(result) == 3
        assert result.count("/path/to/skill2") == 1

    def test_deduplication_by_name_later_wins(self, tmp_path):
        """Same skill name from different paths - later wins."""
        # Arrange
        # First registry has skill with name "shared-skill"
        skill1_dir = tmp_path / "skill1"
        skill1_dir.mkdir()
        (skill1_dir / "SKILL.yaml").write_text("name: shared-skill\n")

        # Second registry also has skill with name "shared-skill"
        skill2_dir = tmp_path / "skill2"
        skill2_dir.mkdir()
        (skill2_dir / "SKILL.yaml").write_text("name: shared-skill\n")

        registry1 = InMemorySkillRegistry([str(skill1_dir)])
        registry2 = InMemorySkillRegistry([str(skill2_dir)])
        composite = CompositeSkillRegistry([registry1, registry2])

        # Act
        result = composite.list_skill_paths()

        # Assert
        assert len(result) == 1
        # The later entry (registry2) should win
        assert result[0] == str(skill2_dir)

    def test_project_local_precedence(self, tmp_path):
        """Project-local skills take precedence over user-wide."""
        # Arrange
        # User-wide skill
        user_skill_dir = tmp_path / "user" / "skill"
        user_skill_dir.mkdir(parents=True)
        (user_skill_dir / "SKILL.yaml").write_text("name: user-skill\n")

        # Project-local skill with same name
        project_skill_dir = tmp_path / "project" / "skill"
        project_skill_dir.mkdir(parents=True)
        (project_skill_dir / "SKILL.yaml").write_text("name: user-skill\n")

        user_registry = InMemorySkillRegistry([str(user_skill_dir)])
        project_registry = InMemorySkillRegistry([str(project_skill_dir)])

        # Project registry is second (later) - should take precedence
        composite = CompositeSkillRegistry([user_registry, project_registry])

        # Act
        result = composite.list_skill_paths()

        # Assert
        assert len(result) == 1
        assert result[0] == str(project_skill_dir)

    def test_handles_registry_with_no_skills(self):
        """Empty registry is handled correctly."""
        # Arrange
        registry1 = InMemorySkillRegistry([])
        registry2 = InMemorySkillRegistry(["/path/to/skill1"])
        composite = CompositeSkillRegistry([registry1, registry2])

        # Act
        result = composite.list_skill_paths()

        # Assert
        assert len(result) == 1

    def test_extracts_skill_name_from_yaml(self, tmp_path):
        """Skill name is extracted from SKILL.yaml."""
        # Arrange
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.yaml").write_text("name: my-special-skill\n")

        registry = InMemorySkillRegistry([str(skill_dir)])
        composite = CompositeSkillRegistry([registry])

        # Act
        result = composite.list_skill_paths()

        # Assert
        assert len(result) == 1
        assert "my-skill" in result[0]

    def test_uses_basename_when_no_name_in_yaml(self, tmp_path):
        """Basename is used when SKILL.yaml has no name field."""
        # Arrange
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.yaml").write_text("description: no name field\n")

        registry = InMemorySkillRegistry([str(skill_dir)])
        composite = CompositeSkillRegistry([registry])

        # Act
        result = composite.list_skill_paths()

        # Assert
        assert len(result) == 1
        assert "my-skill" in result[0]
