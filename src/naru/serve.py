from __future__ import annotations

import sys
import tempfile
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit

from watchfiles import watch

from .config import BuildConfig, load_config
from .engine.build import build


class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, base_path: dict, **kwargs):
        self.base_path = base_path
        super().__init__(*args, **kwargs)

    def send_head(self):
        prefix = self.base_path["value"]
        if prefix:
            parsed = urlsplit(self.path)
            if parsed.path == prefix:
                self.send_response(301)
                location = prefix + "/" + ("?" + parsed.query if parsed.query else "")
                self.send_header("Location", location)
                self.end_headers()
                return None
            if not parsed.path.startswith(prefix + "/"):
                self.send_error(404, "Not found")
                return None
        return super().send_head()

    def translate_path(self, path):
        prefix = self.base_path["value"]
        if prefix:
            parsed = urlsplit(path)
            path = parsed.path[len(prefix):] + (
                "?" + parsed.query if parsed.query else ""
            )
        return super().translate_path(path)


def is_source_change(site_root: Path, changed_path: str) -> bool:
    try:
        parts = Path(changed_path).relative_to(site_root).parts
    except ValueError:
        return False
    return bool(parts) and (
        parts == ("naru.yml",)
        or parts[0] in {"content", "templates", "static", "assets"}
    )


def serve(
    site_root: Path, settings: dict, overrides: dict, host: str, port: int,
    include_drafts: bool, include_future: bool,
) -> None:
    with tempfile.TemporaryDirectory(prefix="naru-preview-") as temporary:
        output = Path(temporary) / "output"
        build(BuildConfig(site_root, output, settings, include_drafts, include_future))
        base_path = {"value": settings["base_url"]}
        handler = partial(PreviewHandler, directory=str(output), base_path=base_path)
        server = ThreadingHTTPServer((host, port), handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        print(
            f"[OK] Preview: http://{host}:{server.server_port}{base_path['value']}/",
            flush=True,
        )
        try:
            for changes in watch(site_root):
                if not any(is_source_change(site_root, path) for _, path in changes):
                    continue
                try:
                    updated = load_config(site_root / "naru.yml", overrides=overrides)
                    build(BuildConfig(
                        site_root, output, updated, include_drafts, include_future
                    ))
                    base_path["value"] = updated["base_url"]
                except (ValueError, OSError) as error:
                    print(
                        f"[ERROR] Rebuild failed: {error}", file=sys.stderr, flush=True
                    )
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
            server.server_close()
            thread.join()