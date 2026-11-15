from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from naru.cli import main
from naru.config import ConfigError, load_config

EXAMPLE_CONFIG = (
    Path(__file__).resolve().parents[1] / "examples" / "basic-site" / "naru.yml"
)


class BuildConfigurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "site"
        self.root.mkdir()
        self.config = self.root / "naru.yml"
        self.config.write_text(
            EXAMPLE_CONFIG.read_text(encoding="utf-8"), encoding="utf-8"
        )
        for path in (
            self.root / "content" / "posts",
            self.root / "templates",
            self.root / "static" / "tools",
        ):
            path.mkdir(parents=True)

    def test_invalid_or_unknown_configuration_is_rejected(self) -> None:
        data = yaml.safe_load(self.config.read_text(encoding="utf-8"))
        data["site_origin"] = "https://example.com/a-path"
        self.config.write_text(yaml.safe_dump(data), encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "site_origin"):
            load_config(self.config)
        data["site_origin"] = "https://example.com"
        data["typo"] = True
        self.config.write_text(yaml.safe_dump(data), encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "unknown fields: typo"):
            load_config(self.config)

    def test_existing_unmanaged_output_is_preserved(self) -> None:
        output = self.root / "output"
        output.mkdir()
        sentinel = output / "important.html"
        sentinel.write_text("keep", encoding="utf-8")
        with self.assertRaises(SystemExit) as result:
            main(["build", "--site-root", str(self.root), "--output", str(output)])
        self.assertEqual(result.exception.code, 2)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_source_directory_cannot_be_used_as_output(self) -> None:
        with self.assertRaises(SystemExit) as result:
            main(["build", "--site-root", str(self.root), "--output", "content"])
        self.assertEqual(result.exception.code, 2)
        self.assertTrue((self.root / "content" / "posts").is_dir())

    @patch("naru.cli.subprocess.run")
    def test_build_uses_isolated_process_and_output_ownership(self, run) -> None:
        run.return_value.returncode = 0
        output = self.root / "output"
        args = ["build", "--site-root", str(self.root), "--output", str(output)]
        self.assertEqual(main(args), 0)
        self.assertEqual(
            (output / ".naru-output").read_text(encoding="utf-8"), str(self.root)
        )
        self.assertEqual(run.call_args.kwargs["env"]["NARU_SITE_ROOT"], str(self.root))
        self.assertEqual(run.call_args.kwargs["env"]["NARU_OUTPUT_DIR"], str(output))
        self.assertEqual(main(args), 0)

    def test_build_uses_each_sites_origin_for_generated_cname_and_feed(self) -> None:
        (self.root / "assets").mkdir()
        (self.root / "static" / "CNAME").write_text("stale.example", encoding="utf-8")
        (self.root / "static" / "tools" / "index.html").write_text(
            "{{ NAV_HTML }} {{ FOOTER_HTML }}", encoding="utf-8"
        )
        for name in (
            "template_index.html",
            "template_catalog.html",
            "template_post.html",
            "template_archive.html",
            "partial_head.html",
            "partial_googletag.html",
            "partial_nav.html",
            "partial_footer.html",
        ):
            (self.root / "templates" / name).write_text(
                "{{ HEAD_HTML }} {{ SITE_ORIGIN }} {{ SITE_NAME }}", encoding="utf-8"
            )
        (self.root / "templates" / "partial_head.html").write_text(
            '<meta name="keywords" content="{{ KEYWORDS }}">', encoding="utf-8"
        )
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONPATH"] = str(EXAMPLE_CONFIG.parents[2] / "src")
        data = yaml.safe_load(self.config.read_text(encoding="utf-8"))
        for origin, name, directory in (
            ("https://first.example", "First Site", "first"),
            ("https://second.example", "Second Site", "second"),
        ):
            data["site_origin"] = origin
            data["site_name"] = name
            self.config.write_text(yaml.safe_dump(data), encoding="utf-8")
            output = self.root / directory
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "naru",
                    "build",
                    "--site-root",
                    str(self.root),
                    "--output",
                    str(output),
                ],
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                (output / "CNAME").read_text(encoding="utf-8"),
                origin.removeprefix("https://"),
            )
            self.assertIn(origin, (output / "rss.xml").read_text(encoding="utf-8"))
            home = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn(f'content="{name}, 기술 기록, IT, 문화, 스포츠"', home)


if __name__ == "__main__":
    unittest.main()
