from pathlib import Path
from urllib.parse import unquote

from .config import (
    BASE_URL,
    CATEGORY_URL_PREFIX,
    OUT_DIR,
    POSTS_URL_PREFIX,
    TAG_URL_PREFIX,
)


def _route_prefix(item: dict) -> str:
    if item.get("type") == "post":
        return POSTS_URL_PREFIX
    if item.get("type") == "hub":
        return CATEGORY_URL_PREFIX
    return ""


def content_path(item: dict) -> str:
    parts = [
        part.strip("/")
        for part in (BASE_URL, _route_prefix(item), str(item["slug"]))
        if part.strip("/")
    ]
    return "/" + "/".join(parts) + "/"


def site_root_path() -> str:
    base_path = BASE_URL.strip("/")
    return f"/{base_path}/" if base_path else "/"


def archive_path(prefix: str, slug: str = "") -> str:
    parts = [
        part.strip("/")
        for part in (BASE_URL, prefix, slug)
        if part.strip("/")
    ]
    return "/" + "/".join(parts) + "/"


def tag_path(slug: str) -> str:
    return archive_path(TAG_URL_PREFIX, slug)


def content_output_path(item: dict) -> Path:
    parts = [
        part.strip("/")
        for part in (_route_prefix(item), str(item["slug"]))
        if part.strip("/")
    ]
    return OUT_DIR.joinpath(*parts, "index.html")


def tag_output_path(slug: str) -> Path:
    parts = [unquote(part) for part in TAG_URL_PREFIX.strip("/").split("/") if part]
    parts.append(unquote(slug))
    return OUT_DIR.joinpath(*parts, "index.html")
