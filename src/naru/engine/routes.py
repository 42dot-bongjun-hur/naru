from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from urllib.parse import quote, unquote

from . import config as engine_config

_output_owners: ContextVar[dict] = ContextVar("naru_output_owners")


@contextmanager
def track_output_paths():
    token = _output_owners.set(({}, {}))
    try:
        yield
    finally:
        _output_owners.reset(token)


def claim_output(path: Path, owner: str):
    relative = path.relative_to(engine_config.OUT_DIR)
    owners, descendants = _output_owners.get()
    for existing in (relative, *relative.parents):
        existing_owner = owners.get(existing)
        if existing_owner is not None:
            if relative == existing and owner == existing_owner:
                return
            raise ValueError(
                f"output path {relative} ({owner}) conflicts with "
                f"{existing} ({existing_owner})"
            )
    if relative in descendants:
        existing, existing_owner = descendants[relative]
        raise ValueError(
            f"output path {relative} ({owner}) conflicts with "
            f"{existing} ({existing_owner})"
        )
    owners[relative] = owner
    for parent in relative.parents:
        descendants.setdefault(parent, (relative, owner))


def _route_prefix(item: dict) -> str:
    if item.get("type") == "post":
        return engine_config.POSTS_URL_PREFIX
    if item.get("type") == "hub":
        return engine_config.CATEGORY_URL_PREFIX
    return ""


def content_path(item: dict) -> str:
    parts = [
        part.strip("/")
        for part in (
            engine_config.BASE_URL,
            _route_prefix(item),
            quote(str(item["slug"]), safe="-._~"),
        )
        if part.strip("/")
    ]
    return "/" + "/".join(parts) + "/"


def site_root_path() -> str:
    base_path = engine_config.BASE_URL.strip("/")
    return f"/{base_path}/" if base_path else "/"


def archive_path(prefix: str, slug: str = "") -> str:
    parts = [
        part.strip("/")
        for part in (engine_config.BASE_URL, prefix, quote(slug, safe="%-._~"))
        if part.strip("/")
    ]
    return "/" + "/".join(parts) + "/"


def tag_path(slug: str) -> str:
    return archive_path(engine_config.TAG_URL_PREFIX, slug)


def content_output_path(item: dict) -> Path:
    parts = [
        part.strip("/")
        for part in (_route_prefix(item), str(item["slug"]))
        if part.strip("/")
    ]
    return engine_config.OUT_DIR.joinpath(*parts, "index.html")


def tag_output_path(slug: str) -> Path:
    parts = [unquote(part) for part in engine_config.TAG_URL_PREFIX.strip("/").split("/") if part]
    parts.append(unquote(slug))
    return engine_config.OUT_DIR.joinpath(*parts, "index.html")
