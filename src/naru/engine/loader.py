import json
import re
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, quote, unquote, urlsplit, urlunsplit
from xml.etree import ElementTree as etree

import markdown
import yaml
from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor
from markdown.treeprocessors import Treeprocessor
from markdown.util import AtomicString

from .config import (
    BASE_URL,
    CATEGORY_URL_PREFIX,
    POSTS_URL_PREFIX,
    SITE_ORIGIN,
    STATIC_DIR,
)
from .metadata import content_sort_key, normalize_metadata

BARE_DOMAIN_PATTERN = r"(?:www\.)?(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}"


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
        site_host = urlsplit(SITE_ORIGIN).hostname
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
                    ("/posts", POSTS_URL_PREFIX),
                    ("/category", CATEGORY_URL_PREFIX),
                ):
                    if parsed_url.path.startswith(old_prefix + "/"):
                        suffix = parsed_url.path[len(old_prefix):].strip("/")
                        route_parts = [
                            part.strip("/")
                            for part in (BASE_URL, new_prefix, suffix)
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
                relative_static_path = source.relative_to(STATIC_DIR.resolve())
            except ValueError:
                relative_static_path = None

            if relative_static_path is not None:
                image.set(
                    "src",
                    urlunsplit((
                        "",
                        "",
                        "/" + quote(
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
                    "/assets/" + quote(asset_path.as_posix(), safe="/:@-._~"),
                    parsed.query,
                    parsed.fragment,
                )),
            )
            self.assets.append((source, Path(*asset_path.parts)))


class BareUrlExtension(Extension):
    def __init__(self, source_dir: Path | None = None, slug: str = "", **kwargs):
        super().__init__(**kwargs)
        self.source_dir = source_dir
        self.slug = slug
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
        md.treeprocessors.register(
            ExternalLinkTreeprocessor(md),
            "external_links",
            5,
        )


def load_markdown_contents(markdown_dir: Path, item_type: str):
    items = []
    if not markdown_dir.exists():
        return items

    for md_file in sorted(markdown_dir.rglob("*.md")):
        raw_text = md_file.read_text(encoding="utf-8-sig")
        if not raw_text.startswith("---"):
            raise ValueError(f"{md_file}: missing YAML front matter")
        parts = raw_text.split("---", 2)
        if len(parts) != 3:
            raise ValueError(f"{md_file}: invalid YAML front matter delimiters")
        meta = yaml.safe_load(parts[1]) or {}
        if not isinstance(meta, dict):
            raise ValueError(f"{md_file}: YAML front matter must be a mapping")
        meta = normalize_metadata(meta, str(md_file))
        content_md = parts[2].strip()

        image_extension = BareUrlExtension(md_file.parent, meta["slug"])
        md = markdown.Markdown(
            extensions=[
                "fenced_code",
                "tables",
                "nl2br",
                "sane_lists",
                "toc",
                image_extension,
            ]
        )
        content_md = linkify_backticked_domains(content_md)
        html_body = md.convert(content_md)

        slug = meta["slug"]
        items.append({
            "slug": slug,
            "type": item_type,
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
            "html_content": html_body,
            "local_image_assets": (
                image_extension.local_image_processor.assets
                if image_extension.local_image_processor
                else []
            ),
            "toc_tokens": md.toc_tokens,
            "meta": meta
        })
    return items


def load_all_contents(data_dir: Path, posts_dir: Path, pages_dir: Path | None = None):
    items = []

    # 1. JSON catalog content
    if data_dir.exists():
        for json_file in sorted(data_dir.glob("*.json")):
            data = json.loads(json_file.read_text(encoding="utf-8"))
            p_info = data.get("page_info", {})
            if not isinstance(p_info, dict):
                raise ValueError(f"{json_file}: page_info must be an object")
            p_info.setdefault("category", "bookmark")
            p_info = normalize_metadata(p_info, str(json_file))
            slug = p_info["slug"]
            if not isinstance(data.get("sites", []), list):
                raise ValueError(f"{json_file}: sites must be a list")
            data["page_info"] = p_info
            for site in data.get("sites", []):
                if not isinstance(site, dict) or "description" not in site:
                    raise ValueError(
                        f"{json_file}: each site must include a description"
                    )
                site["description"] = str(site["description"]).strip()
            items.append({
                "slug": slug,
                "type": "catalog",
                "title": p_info["title"],
                "nav_title": p_info["nav_title"],
                "description": p_info["description"],
                "published_date": p_info["published_date"],
                "updated_date": p_info["updated_date"],
                "links_checked_date": p_info["links_checked_date"],
                "tags": p_info["tags"],
                "footer_link": p_info.get("footer_link") is True,
                "badge": f"#{slug}",
                "stat_text": f"{len(data.get('sites', []))}개 사이트",
                "action_text": "목록 확인하기 →",
                "raw_data": data,
                "meta": p_info,
            })

    items.extend(load_markdown_contents(posts_dir, "post"))
    if pages_dir is not None:
        items.extend(load_markdown_contents(pages_dir, "page"))

    items.sort(key=content_sort_key, reverse=True)
    return items