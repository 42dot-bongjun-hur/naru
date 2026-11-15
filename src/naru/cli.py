from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .config import ConfigError, load_config


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="naru",
        description="A shared Python static site generator.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    commands = parser.add_subparsers(dest="command")
    build_parser = commands.add_parser(
        "build",
        help="Build a site using Naru.",
        description="Build the site rooted at --site-root.",
    )
    build_parser.add_argument(
        "--site-root",
        type=Path,
        default=Path.cwd(),
        help="Site project directory (default: current directory).",
    )
    build_parser.add_argument(
        "--output",
        type=Path,
        help="Output directory (default: <site-root>/docs); empty or Naru-managed.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)
    if args.command == "build":
        site_root = args.site_root.expanduser().resolve()
        if not site_root.is_dir():
            parser.error(f"site root does not exist: {site_root}")
        try:
            load_config(site_root / "naru.yml")
        except ConfigError as error:
            parser.error(str(error))
        if args.output is not None:
            output_dir = args.output.expanduser()
            if not output_dir.is_absolute():
                output_dir = site_root / output_dir
        else:
            output_dir = site_root / "docs"
        output_dir = output_dir.resolve()
        protected = [
            site_root / name for name in ("content", "templates", "static", "assets")
        ]
        protected.append(Path(__file__).resolve().parent)
        if output_dir == site_root or any(
            output_dir == path.resolve()
            or output_dir in path.resolve().parents
            or path.resolve() in output_dir.parents
            for path in protected
        ):
            parser.error(
                f"output directory overlaps site sources or Naru: {output_dir}"
            )
        for required in (("content", "posts"), ("templates",), ("static", "tools")):
            path = site_root.joinpath(*required)
            if not path.is_dir():
                parser.error(f"missing required site directory: {path}")
        marker = output_dir / ".naru-output"
        try:
            if output_dir.exists():
                if not output_dir.is_dir():
                    parser.error(f"output is not a directory: {output_dir}")
                if any(output_dir.iterdir()):
                    if not marker.is_file() or marker.read_text(
                        encoding="utf-8"
                    ) != str(site_root):
                        parser.error(
                            f"output is not managed by Naru for this site: "
                            f"{output_dir}; choose an empty directory"
                        )
            else:
                output_dir.mkdir(parents=True)
            marker.write_text(str(site_root), encoding="utf-8")
        except OSError as error:
            parser.error(f"cannot prepare output directory {output_dir}: {error}")
        env = os.environ.copy()
        env["NARU_SITE_ROOT"] = str(site_root)
        env["NARU_OUTPUT_DIR"] = str(output_dir)
        return subprocess.run(
            [sys.executable, "-m", "naru.engine.build"],
            env=env,
            check=False,
        ).returncode
    elif not argv:
        parser.print_help()
    return 0
