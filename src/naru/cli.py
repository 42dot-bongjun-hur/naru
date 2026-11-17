from __future__ import annotations

import argparse
import tempfile
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .config import BuildConfig, ConfigError, load_config


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
        "--output",
        type=Path,
        help="Output directory (default: <site-root>/docs); empty or Naru-managed.",
    )
    check_parser = commands.add_parser(
        "check", help="Validate a site without changing its output."
    )
    serve_parser = commands.add_parser(
        "serve", help="Preview a site and rebuild when source files change."
    )
    serve_parser.add_argument(
        "--host", default="127.0.0.1", help="Preview bind address."
    )
    serve_parser.add_argument("--port", type=int, default=8000, help="Preview port.")
    for subparser in (build_parser, check_parser, serve_parser):
        subparser.add_argument(
            "--site-root", type=Path, default=Path.cwd(),
            help="Site project directory (default: current directory).",
        )
        subparser.add_argument(
            "--site-origin",
            help="Override site_origin from naru.yml with the published origin.",
        )
        subparser.add_argument(
            "--base-url", help="Override base_url from naru.yml."
        )
        subparser.add_argument(
            "--include-drafts", action="store_true", help="Include draft content."
        )
        subparser.add_argument(
            "--include-future", action="store_true",
            help="Include future-dated content.",
        )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)
    if args.command in {"build", "check", "serve"}:
        site_root = args.site_root.expanduser().resolve()
        if not site_root.is_dir():
            parser.error(f"site root does not exist: {site_root}")
        try:
            overrides = {
                key: value
                for key, value in (
                    ("site_origin", args.site_origin),
                    ("base_url", args.base_url),
                )
                if value is not None
            }
            settings = load_config(site_root / "naru.yml", overrides=overrides)
        except ConfigError as error:
            parser.error(str(error))
        if args.command == "serve":
            from .serve import serve

            if not 0 <= args.port <= 65535:
                parser.error("port must be between 0 and 65535")
            try:
                serve(
                    site_root, settings, overrides, args.host, args.port,
                    args.include_drafts, args.include_future,
                )
            except (ValueError, OSError) as error:
                parser.error(str(error))
            return 0
        if args.command == "check":
            from .engine.build import build

            try:
                with tempfile.TemporaryDirectory(prefix="naru-check-") as temporary:
                    build(BuildConfig(
                        site_root, Path(temporary) / "output", settings,
                        args.include_drafts, args.include_future,
                    ))
            except (ValueError, OSError) as error:
                parser.error(str(error))
            print("[OK] Site check complete; no site output was changed.")
            return 0
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
        for name in ("content", "templates", "static", "assets"):
            path = site_root / name
            if path.exists() and not path.is_dir():
                parser.error(f"site source is not a directory: {path}")
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
        from .engine.build import build

        try:
            build(BuildConfig(
                site_root, output_dir, settings,
                args.include_drafts, args.include_future,
            ))
        except (ValueError, OSError) as error:
            parser.error(str(error))
        return 0
    elif not argv:
        parser.print_help()
    return 0
