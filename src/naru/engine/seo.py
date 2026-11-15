from datetime import UTC, date, datetime, time
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape

from .config import (
    OUT_DIR,
    RSS_DESCRIPTION,
    RSS_ITEM_LIMIT,
    RSS_TITLE,
    SITE_NAME,
    SITE_ORIGIN,
    SITE_TAGLINE,
)
from .routes import content_path, site_root_path


def extract_host(url_str: str) -> str:
    try:
        return urlparse(url_str).netloc or url_str
    except Exception:
        return url_str

def generate_github_pages_meta() -> str:
    """docs/CNAME 및 docs/.nojekyll 파일 생성"""
    domain = extract_host(SITE_ORIGIN)
    (OUT_DIR / "CNAME").write_text(domain, encoding="utf-8")
    (OUT_DIR / ".nojekyll").write_text("", encoding="utf-8")
    print(f"[OK] CNAME & .nojekyll 생성 완료 ({domain})")
    return domain

def generate_sitemap(contents: list, archive_paths=()):
    """표준 Sitemap XML 생성"""
    urls = [f"""  <url>
    <loc>{SITE_ORIGIN}{site_root_path()}</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>"""]

    for path in archive_paths:
        urls.append(f"""  <url>
    <loc>{SITE_ORIGIN}{path}</loc>
  </url>""")

    for item in contents:
        last_mod = item.get("updated_date", "")
        last_mod_tag = (
            f"\n    <lastmod>{last_mod}T00:00:00.000Z</lastmod>"
            if last_mod else ""
        )
        canonical_path = content_path(item)
        urls.append(f"""  <url>
    <loc>{SITE_ORIGIN}{canonical_path}</loc>{last_mod_tag}
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>""")

    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"
        xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">
{chr(10).join(urls)}
</urlset>"""

    (OUT_DIR / "sitemap.xml").write_text(xml_content, encoding="utf-8")
    print("[OK] sitemap.xml 생성 완료")

def generate_rss(contents: list):
    """RFC-822 표준 RSS 2.0 피드 생성"""
    items = []

    ordered_contents = sorted(
        contents,
        key=lambda item: (item["published_date"], item["slug"]),
        reverse=True,
    )[:RSS_ITEM_LIMIT]
    for item in ordered_contents:
        title = item["title"]
        desc = item["description"]
        canonical_path = content_path(item)
        page_link = f"{SITE_ORIGIN}{canonical_path}"

        date_value = item["published_date"]
        published_at = datetime.combine(
            date.fromisoformat(date_value), time.min, tzinfo=UTC
        )
        pub_date_str = published_at.strftime("%a, %d %b %Y %H:%M:%S GMT")

        items.append(f"""    <item>
      <title>{escape(title)}</title>
      <link>{page_link}</link>
      <guid isPermaLink="true">{page_link}</guid>
      <description>{escape(desc)}</description>
      <pubDate>{pub_date_str}</pubDate>
    </item>""")

    rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{escape(RSS_TITLE)}</title>
    <link>{SITE_ORIGIN}{site_root_path()}</link>
    <description>{escape(RSS_DESCRIPTION)}</description>
{chr(10).join(items)}
  </channel>
</rss>"""

    (OUT_DIR / "rss.xml").write_text(rss_content, encoding="utf-8")
    (OUT_DIR / "feed.xml").write_text(rss_content, encoding="utf-8")
    print(f"[OK] rss.xml & feed.xml 생성 완료 ({len(ordered_contents)}개 항목)")

def generate_robots():
    """robots.txt 생성"""
    content = f"""User-agent: *
Allow: /
Sitemap: {SITE_ORIGIN}{site_root_path()}sitemap.xml
"""
    (OUT_DIR / "robots.txt").write_text(content, encoding="utf-8")
    print("[OK] robots.txt 생성 완료")

def generate_page_og_image(assets_dir: Path, filename: str, code_label: str, title: str, site_domain: str):
    """800x420 노션 감성 SVG OG 이미지 생성"""
    title_line1 = title
    title_line2 = ""
    if len(title) > 16:
        split_idx = title.find(" ", 12)
        if split_idx != -1:
            title_line1 = title[:split_idx]
            title_line2 = title[split_idx+1:]

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 420" width="800" height="420">
  <rect width="800" height="420" fill="#ffffff" />
  <rect x="16" y="16" width="768" height="388" rx="12" fill="none" stroke="#f1f5f9" stroke-width="2" />
  <g transform="translate(560, 90)">
    <rect x="60" y="-10" width="120" height="130" rx="8" fill="#dbeafe" opacity="0.6" />
    <circle cx="160" cy="180" r="40" fill="#fee2e2" opacity="0.6" />
    <path d="M 30,20 L 130,20 L 160,50 L 160,210 L 30,210 Z" fill="#ffffff" stroke="#0f172a" stroke-width="3.5" stroke-linejoin="round" />
    <path d="M 130,20 L 130,50 L 160,50" fill="none" stroke="#0f172a" stroke-width="3" stroke-linejoin="round" />
    <line x1="55" y1="80" x2="110" y2="80" stroke="#94a3b8" stroke-width="3" stroke-linecap="round" stroke-dasharray="6,4" />
    <line x1="55" y1="110" x2="135" y2="110" stroke="#cbd5e1" stroke-width="2.5" stroke-linecap="round" />
    <line x1="55" y1="135" x2="125" y2="135" stroke="#cbd5e1" stroke-width="2.5" stroke-linecap="round" />
    <line x1="55" y1="160" x2="95" y2="160" stroke="#cbd5e1" stroke-width="2.5" stroke-linecap="round" />
    <circle cx="30" cy="20" r="14" fill="#2563eb" stroke="#0f172a" stroke-width="3" />
    <circle cx="28" cy="18" r="4" fill="#ffffff" />
    <line x1="30" y1="34" x2="30" y2="52" stroke="#0f172a" stroke-width="3" stroke-linecap="round" />
  </g>
  <g transform="translate(64, 76)">
    <rect width="32" height="32" rx="6" fill="#0f172a" />
    <text x="16" y="22" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="18" font-weight="900" fill="#ffffff">P</text>
    <text x="44" y="23" font-family="-apple-system, BlinkMacSystemFont, 'Pretendard', sans-serif" font-size="20" font-weight="800" fill="#0f172a" letter-spacing="-0.02em">{escape(SITE_NAME)}</text>
    <text x="108" y="22" font-family="-apple-system, BlinkMacSystemFont, monospace" font-size="12" font-weight="600" fill="#2563eb">{code_label}</text>
  </g>
  <text x="64" y="170" font-family="-apple-system, BlinkMacSystemFont, 'Pretendard', sans-serif" font-size="32" font-weight="800" fill="#0f172a" letter-spacing="-0.03em">{escape(title_line1)}</text>
  <text x="64" y="218" font-family="-apple-system, BlinkMacSystemFont, 'Pretendard', sans-serif" font-size="32" font-weight="800" fill="#0f172a" letter-spacing="-0.03em">{escape(title_line2)}</text>
  <text x="64" y="278" font-family="-apple-system, BlinkMacSystemFont, 'Pretendard', sans-serif" font-size="16" font-weight="500" fill="#64748b">{escape(SITE_TAGLINE)}</text>
  <text x="64" y="348" font-family="-apple-system, BlinkMacSystemFont, monospace" font-size="14" font-weight="600" fill="#94a3b8" letter-spacing="0.05em">{site_domain}</text>
</svg>"""

    (assets_dir / filename).write_text(svg_content, encoding="utf-8")
    print(f"[OK] docs/assets/{filename} 생성 완료")