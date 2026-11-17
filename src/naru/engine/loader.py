import re
import sys
import unicodedata
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, quote, unquote, urlsplit, urlunsplit
from xml.etree import ElementTree as etree

import markdown
import yaml
from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor
from markdown.treeprocessors import Treeprocessor
from markdown.util import AtomicString

from . import config as engine_config
from .metadata import content_sort_key, normalize_metadata
from .routes import content_output_path, content_path

BARE_DOMAIN_PATTERN = r"(?:www\.)?(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}"


def slugify_heading(value: str, separator: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    cleaned = re.sub(r"[^\w\s-]", "", normalized)
    slug = re.sub(r"[\s-]+", separator, cleaned).strip(separator)
    return slug or "section"


def linkify_backticked_domains(content: str) -> str:
    pattern = re.compile(r"`(" + BARE_DOMAIN_PATTERN + r")`")
    return pattern.sub(lambda match: f"[{match.group(1)}](https://{match.group(1)})", content)


class BareUrlInlineProcessor(InlineProcessor):
    def handleMatch(self, match, data):
        url = match.group(0)
        while url and url[-1] in ".,!?;:":
            url = url[:-1]
        while url.endswith(")") and url.count(")") > url.count("("):
            url = url[:-1]
        while url.endswith("]") and url.count("]") > url.count("["):
            url = url[:-1]

        if not url or (
            not url.startswith(("http://", "https://"))
            and url.lower().endswith(".md")
        ):
            return None, None, None

        href = url if url.startswith(("http://", "https://")) else f"https://{url}"
        link = etree.Element("a", href=href)
        link.text = AtomicString(url)
        return link, match.start(), match.start() + len(url)


class ExternalLinkTreeprocessor(Treeprocessor):
    def run(self, root):
        site_host = urlsplit(engine_config.SITE_ORIGIN).hostname
        site_host = site_host.lower() if site_host else ""
        if site_host.startswith("www."):
            site_host = site_host[4:]

        for link in root.iter("a"):
            href = link.get("href", "")
            try:
                parsed_url = urlsplit(href)
            except ValueError:
                continue
            link_host = parsed_url.hostname
            if parsed_url.scheme not in ("http", "https") or not link_host:
                continue

            link_host = link_host.lower()
            if link_host.startswith("www."):
                link_host = link_host[4:]
            if link_host == site_host:
                for old_prefix, new_prefix in (
                    ("/posts", engine_config.POSTS_URL_PREFIX),
                    ("/category", engine_config.CATEGORY_URL_PREFIX),
                ):
                    if parsed_url.path.startswith(old_prefix + "/"):
                        suffix = parsed_url.path[len(old_prefix):].strip("/")
                        route_parts = [
                            part.strip("/")
                            for part in (engine_config.BASE_URL, new_prefix, suffix)
                            if part.strip("/")
                        ]
                        link.set(
                            "href",
                            urlunsplit(parsed_url._replace(
                                path="/" + "/".join(route_parts) + "/"
                            )),
                        )
                        break
                continue

            link.set("target", "_blank")
            rel_values = link.get("rel", "").split()
            if "noopener" not in rel_values:
                rel_values.append("noopener")
            link.set("rel", " ".join(rel_values))


class MarkdownLinkTreeprocessor(Treeprocessor):
    def __init__(self, md, source_file: Path, targets: dict):
        super().__init__(md)
        self.source_file = source_file
        self.targets = targets

    def run(self, root):
        for link in root.iter("a"):
            href = link.get("href", "")
            try:
                parsed = urlsplit(href)
            except ValueError:
                continue
            if (
                parsed.scheme
                or parsed.netloc
                or not parsed.path
                or parsed.path.startswith("/")
                or not parsed.path.lower().endswith(".md")
            ):
                continue
            target = (self.source_file.parent / unquote(parsed.path)).resolve()
            path = self.targets.get(target)
            if path is None:
                print(
                    f"[WARNING] {self.source_file}: Markdown link target is not a "
                    f"built document: {href}",
                    file=sys.stderr,
                )
                continue
            link.set("href", urlunsplit(("", "", path, parsed.query, parsed.fragment)))


class YouTubeEmbedTreeprocessor(Treeprocessor):
    def run(self, root):
        for paragraph in root.iter("p"):
            if len(paragraph) != 1 or paragraph.text and paragraph.text.strip():
                continue

            link = paragraph[0]
            if link.tag != "a" or len(link) or link.tail and link.tail.strip():
                continue

            label = (link.text or "").strip()
            prefix = "YouTube 미리보기:"
            if not label.startswith(prefix):
                continue

            video_id = self._video_id(link.get("href", ""))
            if not video_id:
                continue

            title = label[len(prefix):].strip() or "YouTube 영상"
            paragraph.tag = "div"
            paragraph.attrib.clear()
            paragraph.set("class", "youtube-embed")
            paragraph.text = None
            paragraph.remove(link)
            etree.SubElement(paragraph, "iframe", {
                "src": f"https://www.youtube-nocookie.com/embed/{video_id}",
                "title": title,
                "loading": "lazy",
                "referrerpolicy": "strict-origin-when-cross-origin",
                "allow": "accelerometer; encrypted-media; gyroscope; picture-in-picture; web-share",
                "allowfullscreen": "",
            })
            fallback_element = etree.Element("a", {
                "href": link.get("href", ""),
                "class": "youtube-embed-link",
                "aria-label": f"{title} YouTube에서 열기",
            })
            fallback_element.text = "YouTube에서 열기 ↗"
            for parent in root.iter():
                children = list(parent)
                if paragraph in children:
                    parent.insert(children.index(paragraph) + 1, fallback_element)
                    break

    @staticmethod
    def _video_id(url: str) -> str:
        try:
            parsed = urlsplit(url)
            host = parsed.hostname or ""
            if parsed.scheme not in {"http", "https"} or host not in {
                "youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"
            }:
                return ""

            if host == "youtu.be":
                video_id = parsed.path.strip("/").split("/", 1)[0]
            elif parsed.path == "/watch":
                video_id = parse_qs(parsed.query).get("v", [""])[0]
            else:
                path_parts = parsed.path.strip("/").split("/")
                video_id = (
                    path_parts[1]
                    if len(path_parts) == 2 and path_parts[0] in {"embed", "shorts"}
                    else ""
                )
        except ValueError:
            return ""

        return video_id if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id) else ""


class LocalImageTreeprocessor(Treeprocessor):
    def __init__(self, md, source_dir: Path, slug: str):
        super().__init__(md)
        self.source_dir = source_dir.resolve()
        self.slug = slug
        self.assets = []

    def run(self, root):
        for image in root.iter("img"):
            src = image.get("src", "")
            parsed = urlsplit(src)
            if (
                parsed.scheme
                or parsed.netloc
                or not parsed.path
                or parsed.path.startswith("/")
            ):
                continue

            relative_source = Path(unquote(parsed.path.replace("\\", "/")))
            source = (self.source_dir / relative_source).resolve()
            try:
                relative_static_path = source.relative_to(engine_config.STATIC_DIR.resolve())
            except ValueError:
                relative_static_path = None

            if relative_static_path is not None:
                image.set(
                    "src",
                    urlunsplit((
                        "",
                        "",
                        engine_config.BASE_URL + "/" + quote(
                            relative_static_path.as_posix(),
                            safe="/:@-._~",
                        ),
                        parsed.query,
                        parsed.fragment,
                    )),
                )
                continue

            try:
                relative_asset = source.relative_to(self.source_dir)
            except ValueError as error:
                raise ValueError(
                    f"{self.source_dir}: local image path escapes the post folder: {src}"
                ) from error
            if not source.is_file():
                raise FileNotFoundError(
                    f"{self.source_dir}: referenced local image does not exist: {src}"
                )

            asset_path = PurePosixPath("posts") / self.slug / relative_asset.as_posix()
            image.set(
                "src",
                urlunsplit((
                    "",
                    "",
                    engine_config.BASE_URL + "/assets/" + quote(
                        asset_path.as_posix(), safe="/:@-._~"
                    ),
                    parsed.query,
                    parsed.fragment,
                )),
            )
            self.assets.append((source, Path(*asset_path.parts)))


class BareUrlExtension(Extension):
    def __init__(
        self, source_dir: Path | None = None, slug: str = "",
        source_file: Path | None = None, link_targets: dict | None = None, **kwargs,
    ):
        super().__init__(**kwargs)
        self.source_dir = source_dir
        self.slug = slug
        self.source_file = source_file
        self.link_targets = link_targets or {}
        self.local_image_processor = None

    def extendMarkdown(self, md):
        md.inlinePatterns.register(
            BareUrlInlineProcessor(
                r"https?://[^\s<>]+|(?<![\w/@])"
                + BARE_DOMAIN_PATTERN
                + r"(?::\d+)?(?:/[^\s<>]*)?(?:\?[^\s<>]*)?(?:#[^\s<>]*)?",
                md,
            ),
            "bare_url",
            85,
        )
        md.treeprocessors.register(
            YouTubeEmbedTreeprocessor(md),
            "youtube_embed",
            6,
        )
        if self.source_dir is not None:
            self.local_image_processor = LocalImageTreeprocessor(
                md, self.source_dir, self.slug
            )
            md.treeprocessors.register(
                self.local_image_processor,
                "local_images",
                7,
            )
        if self.source_file is not None:
            md.treeprocessors.register(
                MarkdownLinkTreeprocessor(md, self.source_file, self.link_targets),
                "markdown_links",
                8,
            )
        md.treeprocessors.register(
            ExternalLinkTreeprocessor(md),
            "external_links",
            5,
        )


def load_markdown_contents(markdown_dir: Path, item_type: str):
    items = _read_markdown_contents(markdown_dir, item_type)
    _render_markdown_contents(items)
    return items


def _read_markdown_contents(
    markdown_dir: Path, item_type: str, *, include_drafts=False, include_future=False,
    today=None,
):
    items = []
    if not markdown_dir.exists():
        return items
    today = today or datetime.now(UTC).date().isoformat()

    for md_file in sorted(markdown_dir.rglob("*.md")):
        raw_text = md_file.read_text(encoding="utf-8-sig")
        lines = raw_text.splitlines()
        if not lines or lines[0] != "---":
            raise ValueError(f"{md_file}: missing YAML front matter")

        try:
            closing_delimiter = lines.index("---", 1)
        except ValueError as error:
            raise ValueError(
                f"{md_file}: invalid YAML front matter delimiters"
            ) from error

        try:
            meta = yaml.safe_load("\n".join(lines[1:closing_delimiter])) or {}
        except yaml.YAMLError as error:
            mark = getattr(error, "problem_mark", None)
            line_number = mark.line + 2 if mark else None
            location = f"{md_file}:{line_number}" if line_number else str(md_file)
            problem = getattr(error, "problem", None) or str(error).splitlines()[0]
            raise ValueError(
                f"{location}: invalid YAML front matter: {problem}"
            ) from error
        if not isinstance(meta, dict):
            raise ValueError(f"{md_file}: YAML front matter must be a mapping")
        layout = meta.pop("layout", None)
        if layout not in (None, "catalog"):
            raise ValueError(f"{md_file}: layout must be 'catalog' when specified")
        if layout == "catalog" and item_type != "post":
            raise ValueError(f"{md_file}: catalog layout is only supported for posts")
        if "sites" in meta:
            raise ValueError(
                f"{md_file}: move front matter sites to "
                f"{md_file.with_suffix('.sites.yml').name} and use layout: catalog"
            )
        relative_parts = md_file.relative_to(markdown_dir).parts
        if item_type == "post" and len(relative_parts) > 1:
            meta.setdefault("category", relative_parts[0])
        if layout == "catalog":
            meta.setdefault("category", "bookmark")
        meta = normalize_metadata(meta, str(md_file))
        if meta.get("draft", False) and not include_drafts:
            continue
        if meta["published_date"] > today and not include_future:
            continue
        catalog_sites = (
            load_catalog_sites(md_file.with_suffix(".sites.yml"))
            if layout == "catalog"
            else None
        )
        content_md = "\n".join(lines[closing_delimiter + 1:]).strip()

        slug = meta["slug"]
        item = {
            "slug": slug,
            "type": "catalog" if layout == "catalog" else item_type,
            "source_path": md_file,
            "title": meta["title"],
            "nav_title": meta["nav_title"],
            "description": meta["description"],
            "published_date": meta["published_date"],
            "updated_date": meta["updated_date"],
            "tags": meta["tags"],
            "footer_link": meta.get("footer_link") is True,
            "badge": f"#{meta.get('category', item_type.upper())}",
            "stat_text": meta.get("category", "문서"),
            "action_text": "문제 해결법 보기 →",
            "_markdown_source": content_md,
            "meta": meta,
        }
        if layout == "catalog":
            item.update({
                "links_checked_date": meta["links_checked_date"],
                "badge": f"#{slug}",
                "stat_text": f"{len(catalog_sites)}개 사이트",
                "action_text": "목록 확인하기 →",
                "raw_data": {"page_info": meta, "sites": catalog_sites},
            })
        items.append(item)
    return items


def _render_markdown_contents(items: list[dict]):
    targets = {item["source_path"].resolve(): content_path(item) for item in items}
    for item in items:
        source_file = item["source_path"]
        extension = BareUrlExtension(
            source_file.parent, item["slug"], source_file, targets
        )
        md = markdown.Markdown(
            extensions=[
                "extra",
                "nl2br",
                "sane_lists",
                "toc",
                "pymdownx.superfences",
                "pymdownx.tasklist",
                "pymdownx.tilde",
                extension,
            ],
            extension_configs={"toc": {"slugify": slugify_heading}},
        )
        item["html_content"] = md.convert(
            linkify_backticked_domains(item.pop("_markdown_source"))
        )
        item["local_image_assets"] = extension.local_image_processor.assets
        item["toc_tokens"] = md.toc_tokens
        if item["type"] == "catalog":
            item["markdown_intro_html"] = item["html_content"]


def load_catalog_sites(path: Path):
    try:
        sites = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as error:
        raise ValueError(f"{path}: catalog sites file is missing") from error
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise ValueError(f"{path}: cannot read catalog sites: {error}") from error

    if not isinstance(sites, list):
        raise ValueError(f"{path}: catalog sites must be a list")
    ids = set()
    for index, site in enumerate(sites, start=1):
        source = f"{path}: item {index}"
        if not isinstance(site, dict):
            raise ValueError(f"{source}: must be a mapping")
        unknown = set(site) - {"id", "name", "url", "description", "status"}
        if unknown:
            raise ValueError(f"{source}: unknown fields: {', '.join(map(str, unknown))}")
        for field in ("id", "name", "url", "description"):
            value = site.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{source}: {field} must be a non-empty string")
            site[field] = value.strip()
        site_id = site["id"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", site_id):
            raise ValueError(f"{source}: id must be lowercase kebab-case")
        if site_id in ids:
            raise ValueError(f"{source}: duplicate id: {site_id}")
        ids.add(site_id)
        try:
            parsed = urlsplit(site["url"])
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or any(char.isspace() or ord(char) < 32 for char in site["url"])
            ):
                raise ValueError
            parsed.port
        except ValueError as error:
            raise ValueError(f"{source}: url must be an HTTP(S) URL") from error
        status = site.get("status", "unknown")
        if not isinstance(status, str) or status not in {
            "active", "inactive", "error", "unknown"
        }:
            raise ValueError(f"{source}: status must be active, inactive, error, or unknown")
    return sites


def load_all_contents(
    data_dir: Path, posts_dir: Path, pages_dir: Path | None = None, *,
    include_drafts=False, include_future=False,
):
    items = []
    today = datetime.now(UTC).date().isoformat()

    if data_dir.exists():
        legacy_catalogs = sorted(data_dir.glob("*.json"))
        if legacy_catalogs:
            raise ValueError(
                f"{legacy_catalogs[0]}: JSON catalogs are no longer supported; "
                "move the page to Markdown and its sites to a matching .sites.yml file"
            )

    items.extend(_read_markdown_contents(
        posts_dir, "post", include_drafts=include_drafts, include_future=include_future,
        today=today,
    ))
    if pages_dir is not None:
        items.extend(_read_markdown_contents(
            pages_dir, "page", include_drafts=include_drafts, include_future=include_future,
            today=today,
        ))

    output_sources = {}
    for item in items:
        output_path = content_output_path(item)
        if output_path in output_sources:
            raise ValueError(
                f"{item['source_path']}: output path {output_path} conflicts with "
                f"{output_sources[output_path]}"
            )
        output_sources[output_path] = item["source_path"]

    _render_markdown_contents(items)
    items.sort(key=content_sort_key, reverse=True)
    return items