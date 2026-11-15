from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
        return subprocess.run(
            [sys.executable, "-m", "naru", *args],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_version_option(self) -> None:
        result = self.run_cli("--version")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "naru 0.1.2")

    def test_no_arguments_prints_help(self) -> None:
        result = self.run_cli()
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage: naru", result.stdout)

    def test_build_rejects_missing_site_root(self) -> None:
        result = self.run_cli(
            "build",
            "--site-root",
            str(PROJECT_ROOT / "missing-site"),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("site root does not exist", result.stderr)


if __name__ == "__main__":
    unittest.main()
