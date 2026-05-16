"""Environment variables and constants."""

import os
from pathlib import Path

STEPLOCK_DIR: Path = Path.home() / ".steplock"
SKILLS_REGISTRY_PATH: Path = STEPLOCK_DIR / "skills-registry.yaml"

PROJECT_STEPLOCK_DIR: Path = Path(os.getcwd()) / ".steplock"
PROJECT_SKILLS_REGISTRY_PATH: Path = PROJECT_STEPLOCK_DIR / "skills-registry.yaml"
