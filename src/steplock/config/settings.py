"""Environment variables and constants."""

from pathlib import Path

STEPLOCK_DIR: Path = Path.home() / ".steplock"
SKILLS_REGISTRY_PATH: Path = STEPLOCK_DIR / "skills-registry.yaml"
