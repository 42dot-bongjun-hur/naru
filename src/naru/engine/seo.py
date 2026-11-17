from datetime import UTC, date, datetime, time
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as etree

from . import config as engine_config
from .routes import claim_output, content_path, site_root_path
from .templates import render_template


def extract_host(url_str: str) -> str:
    try:
        return urlparse(url_str).netloc or url_str
    except Exception:
        return url_str

def generate_github_pages_meta() -> str:
    """docs/CNAME 및 docs/.nojekyll 파일 생성"""
    domain = extract_host(engine_config.SITE_ORIGIN)
    claim_output(engine_config.OUT_DIR / "CNAME", "GitHub Pages CNAME")
    claim_output(engine_config.OUT_DIR / ".nojekyll", "GitHub Pages marker")
    (engine_config.OUT_DIR / "CNAME").write_text(domain, encoding="utf-8")
    (engine_config.OUT_DIR / ".nojekyll").write_text("", encoding="utf-8")
    print(f"[OK] CNAME & .nojekyll 생성 완료 ({domain})")
    return domain

def generate_sitemap(contents: list, archive_paths=()):
    """표준 Sitemap XML 생성"""
    root = etree.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    home = etree.SubElement(root, "url")
    etree.SubElement(home, "loc").text = engine_config.SITE_ORIGIN + site_root_path()
    etree.SubElement(home, "changefreq").text = "daily"
    etree.SubElement(home, "priority").text = "1.0"
    for path in archive_paths:
        entry = etree.SubElement(root, "url")
        etree.SubElement(entry, "loc").text = engine_config.SITE_ORIGIN + path
    for item in contents:
        entry = etree.SubElement(root, "url")
        etree.SubElement(entry, "loc").text = engine_config.SITE_ORIGIN + content_path(item)
        if item.get("updated_date"):
            etree.SubElement(entry, "lastmod").text = item["updated_date"] + "T00:00:00.000Z"
        etree.SubElement(entry, "changefreq").text = "weekly"
        etree.SubElement(entry, "priority").text = "0.8"
    claim_output(engine_config.OUT_DIR / "sitemap.xml", "sitemap")
    etree.indent(root)
    etree.ElementTree(root).write(
        engine_config.OUT_DIR / "sitemap.xml", encoding="utf-8", xml_declaration=True
    )
    print("[OK] sitemap.xml 생성 완료")


def generate_rss(contents: list):
    """RFC-822 표준 RSS 2.0 피드 생성"""
    root = etree.Element("rss", version="2.0")
    channel = etree.SubElement(root, "channel")
    etree.SubElement(channel, "title").text = engine_config.RSS_TITLE
    etree.SubElement(channel, "link").text = engine_config.SITE_ORIGIN + site_root_path()
    etree.SubElement(channel, "description").text = engine_config.RSS_DESCRIPTION
    ordered_contents = sorted(
        contents,
        key=lambda item: (item["published_date"], item["slug"]),
        reverse=True,
    )[:engine_config.RSS_ITEM_LIMIT]
    for item in ordered_contents:
        entry = etree.SubElement(channel, "item")
        page_link = engine_config.SITE_ORIGIN + content_path(item)
        etree.SubElement(entry, "title").text = item["title"]
        etree.SubElement(entry, "link").text = page_link
        etree.SubElement(entry, "guid", isPermaLink="true").text = page_link
        etree.SubElement(entry, "description").text = item["description"]
        published_at = datetime.combine(
            date.fromisoformat(item["published_date"]), time.min, tzinfo=UTC
        )
        etree.SubElement(entry, "pubDate").text = published_at.strftime("%a, %d %b %Y %H:%M:%S GMT")
    etree.indent(root)
    for name in ("rss.xml", "feed.xml"):
        claim_output(engine_config.OUT_DIR / name, f"RSS feed {name}")
        etree.ElementTree(root).write(
            engine_config.OUT_DIR / name, encoding="utf-8", xml_declaration=True
        )
    print(f"[OK] rss.xml & feed.xml 생성 완료 ({len(ordered_contents)}개 항목)")

def generate_robots():
    """정적 robots.txt가 없으면 생성"""
    if (engine_config.STATIC_DIR / "robots.txt").is_file():
        return
    content = f"""User-agent: *
Allow: /
Sitemap: {engine_config.SITE_ORIGIN}{site_root_path()}sitemap.xml
"""
    claim_output(engine_config.OUT_DIR / "robots.txt", "robots.txt")
    (engine_config.OUT_DIR / "robots.txt").write_text(content, encoding="utf-8")
    print("[OK] robots.txt 생성 완료")

def generate_page_og_image(assets_dir: Path, filename: str, code_label: str, title: str, site_domain: str, owner: str):
    """800x420 노션 감성 SVG OG 이미지 생성"""
    title_line1 = title
    title_line2 = ""
    if len(title) > 16:
        split_idx = title.find(" ", 12)
        if split_idx != -1:
            title_line1 = title[:split_idx]
            title_line2 = title[split_idx+1:]

    svg_content = render_template(
        "image_og.svg", code_label=code_label, title_line1=title_line1,
        title_line2=title_line2, site_domain=site_domain,
    )
    claim_output(assets_dir / filename, owner)
    (assets_dir / filename).write_text(svg_content, encoding="utf-8")
    print(f"[OK] docs/assets/{filename} 생성 완료")