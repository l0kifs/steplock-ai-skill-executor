"""YAML-based skill loader."""

from __future__ import annotations

import os

import yaml

from steplock.application.skill.ports import ISkillLoader
from steplock.domains.skill.exceptions import InvalidSkillDefinitionError, SkillNotFoundError
from steplock.domains.skill.models import Skill, Step


class YamlSkillLoader(ISkillLoader):
    def load(self, skill_path: str) -> Skill:
        if os.path.isdir(skill_path):
            yaml_path = os.path.join(skill_path, "SKILL.yaml")
        else:
            yaml_path = skill_path

        if not os.path.exists(yaml_path):
            raise SkillNotFoundError(skill_path)

        base_dir = os.path.dirname(os.path.abspath(yaml_path))

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        try:
            name = data["name"]
            steps_data = data["steps"]
        except (KeyError, TypeError) as e:
            raise InvalidSkillDefinitionError(f"Missing required field in skill definition: {e}") from e

        description = data.get("description", "")

        steps: list[Step] = []
        for step_data in steps_data:
            try:
                step_id = step_data["id"]
                instruction_raw = step_data["instruction"]
            except (KeyError, TypeError) as e:
                raise InvalidSkillDefinitionError(f"Missing required field in step definition: {e}") from e

            # Resolve instruction: treat as file path first, fall back to inline content
            candidate_path = os.path.join(base_dir, instruction_raw)
            if os.path.isfile(candidate_path):
                with open(candidate_path) as f:
                    instruction = f.read()
            else:
                instruction = instruction_raw

            # Resolve verify script to absolute path
            verify_script_path: str | None = None
            if "verify" in step_data and step_data["verify"]:
                verify_script_path = os.path.join(base_dir, step_data["verify"])

            on_fail = step_data.get("on_fail", "abort")
            if on_fail not in ("retry", "abort"):
                raise InvalidSkillDefinitionError(f"Invalid on_fail value '{on_fail}' in step '{step_id}'. Must be 'retry' or 'abort'.")

            steps.append(Step(
                id=step_id,
                instruction=instruction,
                verify_script_path=verify_script_path,
                on_fail=on_fail,
            ))

        return Skill(name=name, description=description, steps=steps)
