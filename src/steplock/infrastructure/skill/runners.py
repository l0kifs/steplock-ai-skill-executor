"""Subprocess-based verification and helper script runners."""

from __future__ import annotations

import subprocess
import sys

from steplock.application.skill.ports import IHelperRunner, IVerificationRunner


class SubprocessVerificationRunner(IVerificationRunner):
    def run(self, script_path: str, output: str) -> tuple[bool, str]:
        """Run a verification script, passing the submitted output via stdin.

        The script is run with the same Python interpreter as the current process.
        Returns (True, "") on exit code 0, or (False, combined_output) on non-zero exit.
        """
        result = subprocess.run(
            [sys.executable, script_path],
            input=output,
            capture_output=True,
            text=True,
        )
        script_output = (result.stdout + result.stderr).strip()
        return result.returncode == 0, script_output


class SubprocessHelperRunner(IHelperRunner):
    def run(self, script_path: str, args: list[str]) -> tuple[str, str, int]:
        """Run a helper script with the given arguments appended to sys.argv.

        The script is run with the same Python interpreter as the current process.
        Returns (stdout, stderr, exit_code).
        """
        result = subprocess.run(
            [sys.executable, script_path, *args],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
        )
        return result.stdout, result.stderr, result.returncode
