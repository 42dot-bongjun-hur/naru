import hashlib
import json
import re
import shutil
import sys
import tempfile
import traceback
import unicodedata
from contextvars import ContextVar
from html.parser import HTMLParser
from importlib.resources import files
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlsplit
from xml.sax.saxutils import escape, quoteattr

from jinja2 import (
    ChoiceLoader,
    Environment,
    FileSystemLoader,
    PackageLoader,
    StrictUndefined,
    TemplateError,
    TemplateNotFound,
    meta,
)
from markupsafe import Markup

from naru.config import BuildConfig
from naru.theme import theme_css

from . import config as engine_config
from .ads import render_ad, render_infeed_ad
from .loader import load_all_contents
from .metadata import content_sort_key, keyword_content
from .routes import (
    archive_path,
    claim_output,
    content_output_path,
    content_path,
    site_root_path,
    tag_output_path,
    tag_path,
    track_output_paths,
)
from .seo import (
    generate_github_pages_meta,
    generate_page_og_image,
    generate_robots,
    generate_rss,
    generate_sitemap,
)

CSS_VERSION: ContextVar[str] = ContextVar("naru_css_version", default="")


def sync_static_files():
    """static/ 폴더 내 파일들을 docs/ 루트로 그대로 복사"""
    if not engine_config.STATIC_DIR.exists():
        return

    copied_count = 0
    for item in engine_config.STATIC_DIR.iterdir():
        dest = engine_config.OUT_DIR / item.name
        if item.is_file():
            shutil.copy2(item, dest)
            copied_count += 1
        elif item.is_dir():
            if item.name == "assets" and (engine_config.BASE_DIR / "assets").is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            copied_count += 1
    print(f"[OK] static/ 파일 동기화 완료 ({copied_count}개)")


def register_source_outputs():
    for root, prefix in (
        (engine_config.STATIC_DIR, Path()),
        (engine_config.BASE_DIR / "assets", Path("assets")),
    ):
        if root.exists():
            for source in sorted(root.rglob("*")):
                if source.is_file():
                    destination = engine_config.OUT_DIR / prefix / source.relative_to(root)
                    if root == engine_config.STATIC_DIR and destination in {
                        engine_config.OUT_DIR / "CNAME", engine_config.OUT_DIR / ".nojekyll"
                    }:
                        continue
                    claim_output(destination, str(source))


def clean_generated_pages():
    """이전 경로의 페이지가 새 빌드 결과에 남지 않도록 HTML 산출물만 제거"""
    removed_count = 0
    for page in engine_config.OUT_DIR.rglob("*.html"):
        page.unlink()
        removed_count += 1
    print(f"[OK] 이전 HTML 산출물 정리 완료 ({removed_count}개)")


class FragmentCollector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.add(attributes["id"])
        if tag == "a":
            if attributes.get("name"):
                self.ids.add(attributes["name"])
            if attributes.get("href"):
                self.links.append(attributes["href"])


def warn_broken_fragments(items):
    documents = {}
    for item in items:
        parser = FragmentCollector()
        parser.feed(content_output_path(item).read_text(encoding="utf-8"))
        documents[content_path(item).rstrip("/")] = (item, parser)
    for path, (item, parser) in documents.items():
        for href in parser.links:
            try:
                link = urlsplit(href)
                if link.scheme or link.netloc or not link.fragment:
                    continue
                target_path = urlsplit(urljoin(path + "/", href)).path.rstrip("/")
            except ValueError:
                continue
            target = documents.get(target_path)
            if target is None:
                continue
            fragment = unquote(link.fragment).split(":~:", 1)[0]
            if fragment and fragment not in target[1].ids:
                print(
                    f"[WARNING] {item['source_path']}: link fragment not found: {href}",
                    file=sys.stderr,
                )


def clean_post_images():
    manifest_path = engine_config.OUT_DIR / ".naru-output-assets.json"
    if not manifest_path.exists():
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or manifest.get("version") != 1:
            raise ValueError("unsupported asset manifest")
        entries = manifest.get("files")
        if not isinstance(entries, list):
            raise ValueError("asset manifest files must be a list")
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("invalid asset manifest entry")
            name, digest = entry.get("path"), entry.get("sha256")
            if not isinstance(name, str) or not isinstance(digest, str):
                raise ValueError("invalid asset manifest path or hash")
            relative = Path(name)
            if (
                relative.is_absolute()
                or "\\" in name
                or len(relative.parts) < 3
                or relative.parts[0] != "posts"
                or any(part in {".", ".."} for part in relative.parts)
                or not re.fullmatch(r"[0-9a-f]{64}", digest)
            ):
                raise ValueError(f"invalid asset manifest entry: {name!r}")
            destination = engine_config.OUT_DIR / "assets" / relative
            if destination.is_file() and hashlib.sha256(destination.read_bytes()).hexdigest() == digest:
                destination.unlink()
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"{manifest_path}: cannot clean generated images: {error}") from error


def sync_post_images(items, docs_assets):
    copied_count = 0
    generated = {}
    for item in items:
        for source, relative_dest in item.get("local_image_assets", []):
            destination = docs_assets / relative_dest
            claim_output(destination, f"attachment {source}")
            if relative_dest in generated and generated[relative_dest] != source:
                raise ValueError(
                    f"{source}: image output {destination} conflicts with "
                    f"{generated[relative_dest]}"
                )
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            generated[relative_dest] = source
            copied_count += 1
    manifest = {
        "version": 1,
        "files": [
            {
                "path": path.as_posix(),
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            }
            for path, source in sorted(generated.items())
        ],
    }
    manifest_path = engine_config.OUT_DIR / ".naru-output-assets.json"
    claim_output(manifest_path, "Naru image manifest")
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"[OK] 게시물 이미지 동기화 완료 ({copied_count}개)")

def create_template_environment(settings: dict) -> Environment:
    environment = Environment(
        loader=ChoiceLoader([
            FileSystemLoader(engine_config.TPL_DIR),
            PackageLoader("naru", "defaults/templates"),
        ]),
        autoescape=True,
        undefined=StrictUndefined,
    )
    environment.globals.update(
        site=settings,
        content_url=content_path,
        tag_url=tag_path,
        archive_url=archive_path,
        site_root_url=site_root_path,
        **{
            key.upper(): value
            for key, value in settings.items()
        },
    )
    return environment


class TemplateFragment:
    def __init__(self, environment, name, context):
        self.environment = environment
        self.name = name
        self.context = context

    def __html__(self):
        template = self.environment.get_template(self.name)
        return template.render(**self.context)

    def __bool__(self):
        return bool(self.__html__())

def render_head(
    tpl_head, title, description, tags, canonical_path, og_image,
    og_type="website", robots="index, follow",
):
    context = {
        "CSS_VERSION": CSS_VERSION.get(),
        "TITLE": title,
        "DESCRIPTION": description,
        "KEYWORDS": keyword_content(tags),
        "CANONICAL_PATH": canonical_path,
        "OG_IMAGE": og_image,
        "OG_TYPE": og_type,
        "ROBOTS": robots,
    }
    context["GOOGLE_TAG"] = TemplateFragment(
        tpl_head.environment, "partial_googletag.html", context.copy()
    )
    return tpl_head.render(**context)

def render_nav(tpl_nav, nav_right_html, top_nav_links):
    return tpl_nav.render(
        TOP_NAV_LINKS=Markup(top_nav_links),
        NAV_RIGHT=Markup(nav_right_html),
    )

def home_group_icon(icon_name):
    paths = {
        "briefcase": '<rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18M10 12v2h4v-2"/>',
        "code": '<path d="m8 8-4 4 4 4M16 8l4 4-4 4M14 5l-4 14"/>',
        "spark": '<path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z"/><path d="m19 16 .8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8L19 16Z"/>',
        "pen": '<path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16v4Z"/><path d="m13.5 6.5 4 4"/>',
        "wrench": '<path d="M14.7 6.3a5 5 0 0 0-6.4 6.4L3 18l3 3 5.3-5.3a5 5 0 0 0 6.4-6.4L14 13l-3-3 3.7-3.7Z"/>',
    }
    return (
        '<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
        'stroke-linejoin="round">'
        + paths.get(icon_name, paths["spark"])
        + "</svg>"
    )

def render_category_group_links(class_name):
    links = []
    for label, _, _, icon_name in engine_config.HOME_CATEGORY_GROUPS:
        href = (
            f"{site_root_path()}tools/"
            if label == "유틸리티"
            else f"{site_root_path()}#home-group-{icon_name}"
        )
        links.append(
            f'<a class="{class_name}-link" href="{href}">'
            f'{home_group_icon(icon_name)}<span>{escape(label)}</span></a>'
        )
    return "".join(links)

def render_footer(tpl_footer, site_domain, pages=()):
    info_links = "".join(
        f'<a href="{content_path(page)}">{escape(page["nav_title"])}</a>'
        for page in pages
    )
    return tpl_footer.render(
        SITE_DOMAIN=site_domain,
        FOOTER_GROUP_LINKS=Markup(render_category_group_links("footer-group")),
        FOOTER_INFO_LINKS=Markup(info_links),
        pages=pages,
    )

def build_tools_page(nav_html, footer_html):
    source_path = engine_config.STATIC_DIR / "tools" / "index.html"
    output_path = engine_config.OUT_DIR / "tools" / "index.html"
    rendered = source_path.read_text(encoding="utf-8") \
                          .replace("{{ NAV_HTML }}", nav_html) \
                          .replace("{{ FOOTER_HTML }}", footer_html)
    if "{{ NAV_HTML }}" in rendered or "{{ FOOTER_HTML }}" in rendered:
        raise ValueError(f"{source_path}: shared navigation or footer placeholder was not rendered")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    print(f"[OK] {output_path.relative_to(engine_config.OUT_DIR)} 공통 헤더/푸터 적용 완료")


def content_category(item, default=""):
    category = item.get("meta", {}).get("category")
    if item.get("type") == "catalog":
        category = category or "bookmark"
    else:
        category = category or default
    return str(category).strip().upper()


def build_home(items, tpl_home, tpl_head, tpl_nav, footer_html, docs_assets, site_domain, top_nav_links, hubs):
    title = engine_config.SITE_TAGLINE
    description = engine_config.SITE_DESCRIPTION
    og_filename = "og-home.svg"
    generate_page_og_image(docs_assets, og_filename, engine_config.SITE_NAME, title, site_domain, "home OG image")

    head_html = render_head(
        tpl_head,
        title=title,
        description=description,
        tags=[engine_config.SITE_NAME, "기술 기록", "IT", "문화", "스포츠"],
        canonical_path=site_root_path(),
        og_image=f"{engine_config.SITE_ORIGIN}{engine_config.BASE_URL}/assets/{og_filename}"
    )

    articles = [
        item for item in items if item["type"] in {"post", "catalog"}
    ]
    # 최신 업데이트 날짜 추출하여 상단바 우측 배지로 표시
    all_dates = [it.get("updated_date", "") for it in items if it.get("updated_date")]
    latest_date = max(all_dates) if all_dates else ""
    nav_html = render_nav(
        tpl_nav,
        f'<span class="nav-status-pill">UPDATED {escape(latest_date)}</span>',
        top_nav_links,
    )

    grouped_articles = {}
    for item in articles:
        category = content_category(item, "NOTE")
        grouped_articles.setdefault(category, []).append(item)

    category_order = [str(category).strip().upper() for category in engine_config.HOME_CATEGORY_ORDER]
    ordered_categories = [category for category in category_order if category in grouped_articles]
    ordered_categories.extend(sorted(set(grouped_articles) - set(ordered_categories)))
    hubs_by_category = {hub["category"].upper(): hub for hub in hubs}
    category_sections = {}
    # 카드가 충분한 카테고리 중 하나 걸러 한 곳씩, 최대 HOME_MAX_ADS개만 광고를 넣는다
    ad_candidates = [c for c in ordered_categories if len(grouped_articles[c]) > 5]
    ad_categories = set((ad_candidates[1::2] or ad_candidates[:1])[:engine_config.HOME_MAX_ADS])
    for category in ordered_categories:
        category_articles = sorted(
            grouped_articles[category],
            key=lambda item: item.get("updated_date", ""),
            reverse=True,
        )
        visible_articles = category_articles[:engine_config.HOME_POSTS_PER_CATEGORY]
        hub = hubs_by_category.get(category)
        category_sections[category] = {
            "label": engine_config.CATEGORY_LABELS.get(category, category),
            "items": visible_articles,
            "count": len(category_articles),
            "show_ad": category in ad_categories,
            "more_url": (
                content_path(hub)
                if len(category_articles) >= engine_config.HOME_POSTS_PER_CATEGORY and hub
                else ""
            ),
        }

    recent_items = sorted(articles, key=lambda item: item.get("updated_date", ""), reverse=True)[:engine_config.HOME_RECENT_POSTS]
    recent_entries = [
        {
            "item": item,
            "category_label": engine_config.CATEGORY_LABELS.get(
                content_category(item), content_category(item)
            ),
        }
        for item in recent_items
    ]

    configured_categories = {
        category
        for _, _, categories, _ in engine_config.HOME_CATEGORY_GROUPS
        for category in categories
    }
    category_groups = list(engine_config.HOME_CATEGORY_GROUPS)
    ungrouped_categories = sorted(set(category_sections) - configured_categories)
    if ungrouped_categories:
        category_groups.append(("기타", "MORE NOTES", tuple(ungrouped_categories), "spark"))

    home_groups = []
    for group_label, group_kicker, group_categories, icon_name in category_groups:
        available_categories = [
            category for category in group_categories if category in category_sections
        ]
        if not available_categories:
            continue
        group_count = sum(len(grouped_articles[category]) for category in available_categories)
        home_groups.append({
            "label": group_label,
            "kicker": group_kicker,
            "icon_name": icon_name,
            "icon": Markup(home_group_icon(icon_name)),
            "count": group_count,
            "categories": [category_sections[category] for category in available_categories],
            "utility_url": f"{engine_config.BASE_URL}/tools/" if group_label == "유틸리티" else "",
        })

    home_context = {
        "home_groups": home_groups,
        "recent_entries": recent_entries,
        "infeed_ad": Markup(render_infeed_ad(engine_config.AD_SLOT_MID)),
    }

    rendered = tpl_home.render(
        HEAD_HTML=Markup(head_html),
        NAV_HTML=Markup(nav_html),
        QUICK_MENU=Markup(""),
        TOPIC_LINKS=Markup(""),
        FOOTER_HTML=Markup(footer_html),
        SLOGAN_EN_PLAIN=engine_config.SITE_SLOGAN_EN,
        SLOGAN_EN=Markup(re.sub(r"\b(Dev|B|J)", r'<span class="slogan-initial">\1</span>', escape(engine_config.SITE_SLOGAN_EN).replace(" Just", "<br>Just"), count=3)),
        SLOGAN_KO=engine_config.SITE_SLOGAN_KO,
        RECENT_POSTS=TemplateFragment(
            tpl_home.environment, "partial_home_recent.html", home_context
        ),
        HOME_CONTENT_SECTIONS=TemplateFragment(
            tpl_home.environment, "partial_home_groups.html", home_context
        ),
        items=items,
        **home_context,
    )
    rendered = "\n".join(line.rstrip() for line in rendered.splitlines()) + "\n"

    output_path = engine_config.OUT_DIR / "index.html"
    claim_output(output_path, "home page")
    output_path.write_text(rendered, encoding="utf-8")
    print("[OK] docs/index.html 생성 완료 (통합 상단바 + 대시보드형 2열 보드)")

def build_catalog(item, nav_items_list, category_nav_list, tpl_cat, tpl_head, tpl_nav, footer_html, docs_assets, site_domain, posts=(), hubs=(), top_nav_links=""):
    code = item["slug"]
    data = item["raw_data"]
    p_info = data.get("page_info", {})
    sites = data.get("sites", [])

    og_filename = f"og-{code}.svg"
    generate_page_og_image(docs_assets, og_filename, f"#{code}", p_info.get("title", f"디렉토리 {code}"), site_domain, f"OG image for {item['source_path']}")

    published_date = item["published_date"]
    updated_date = item["updated_date"]
    links_checked_date = item["links_checked_date"]
    catalog_schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": p_info.get("title", ""),
        "description": p_info.get("description", ""),
        "url": f"{engine_config.SITE_ORIGIN}{content_path(item)}",
        "datePublished": published_date,
        "dateModified": updated_date,
        "isPartOf": {
            "@type": "WebSite",
            "name": engine_config.SITE_NAME,
            "url": f"{engine_config.SITE_ORIGIN}{site_root_path()}",
        },
        "mainEntity": {
            "@type": "ItemList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": index,
                    "name": site.get("name", ""),
                    "url": site.get("url", ""),
                }
                for index, site in enumerate(sites, start=1)
            ],
        },
    }
    json_ld = (
        '<script type="application/ld+json">'
        + json.dumps(catalog_schema, ensure_ascii=False).replace("</", "<\\/")
        + "</script>"
    )

    head_html = render_head(
        tpl_head,
        title=p_info.get("title", ""),
        description=item["description"],
        tags=item["tags"],
        canonical_path=content_path(item),
        og_image=f"{engine_config.SITE_ORIGIN}{engine_config.BASE_URL}/assets/{og_filename}",
        og_type="article"
    ) + "\n" + json_ld

    nav_html = render_nav(
        tpl_nav,
        f'<a href="{site_root_path()}" class="nav-back-link">← 전체 홈</a>',
        top_nav_links,
    )

    toc_items = "".join([
        f'<li><a href="#sec-{s.get("id")}">{i+1:02d}. {escape(s.get("name", ""))}</a></li>\n'
        for i, s in enumerate(sites)
    ])
    intro_guide_html = (
        '<section class="catalog-guide-section" aria-label="이용 안내 및 가이드">'
        + item["markdown_intro_html"]
        + '</section>'
    )
    ad_in_table = Markup(render_ad(engine_config.AD_SLOT_MID))
    context = {
        "HEAD_HTML": Markup(head_html),
        "NAV_HTML": Markup(nav_html),
        "FOOTER_HTML": Markup(footer_html),
        "TITLE": p_info.get("title", ""),
        "DESCRIPTION": item["description"],
        "PUBLISHED_DATE": published_date,
        "UPDATED_DATE": updated_date,
        "LINKS_CHECKED_DATE": links_checked_date,
        "MAINTENANCE_NOTE": p_info.get("maintenance_note", "정기 관리"),
        "CAT_NAV_LINKS": Markup(nav_items_list),
        "CATEGORY_NAV_LINKS": Markup(category_nav_list),
        "TOC_ITEMS": Markup(toc_items),
        "AD_TOP": Markup(render_ad(engine_config.AD_SLOT_TOP, ad_format="horizontal", full_width_responsive=True)),
        "AD_SIDE": Markup(render_ad(engine_config.AD_SLOT_SIDE)),
        "INTRO_GUIDE_HTML": Markup(intro_guide_html),
        "CROSS_PROMO_HTML": Markup(""),
        "SEO_SHIELD_HTML": Markup(""),
        "sites": sites,
        "page": item,
        "AD_IN_TABLE": ad_in_table,
    }
    context["ENTRIES_HTML"] = TemplateFragment(
        tpl_cat.environment, "partial_catalog_entries.html", context.copy()
    )
    rendered_cat = tpl_cat.render(**context)

    output_path = content_output_path(item)
    claim_output(output_path, str(item["source_path"]))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered_cat, encoding="utf-8")
    print(f"[OK] {output_path.relative_to(engine_config.OUT_DIR)} 생성 완료")

HUB_CATEGORIES = {
    "SPORTS": {
        "slug": "sports",
        "title": "골프 / 당구 노트: 입문 기록과 연습 가이드",
        "nav_title": "골프 / 당구",
        "description": "골프 입문과 당구 연습에 관한 기록, 참고한 레슨, 연습 루틴을 모았습니다.",
    },
    "COFFEE": {
        "slug": "coffee",
        "title": "커피 노트: 원두와 바리스타 상식 정리",
        "nav_title": "커피",
        "description": "원두 종류, 로스팅, 블렌딩처럼 커피를 즐기며 배운 내용을 정리했습니다.",
    },
    "BLOG": {
        "slug": "blog",
        "title": "블로그 노트: 다양한 주제의 기록",
        "nav_title": "블로그",
        "description": "여러 주제의 글과 메모를 모았습니다.",
    },
    "DEV": {
        "slug": "dev",
        "title": "개발 / IT 노트: 개발 도구와 기술 운영",
        "nav_title": "개발 / IT",
        "description": "개발 워크플로우, 오픈소스, IT 도구와 기술 주제에 관한 자료와 실전 메모를 모았습니다.",
    },
    "MONEY": {
        "slug": "money",
        "title": "머니 / 혜택 노트: 투자 전략과 알뜰 혜택 정리",
        "nav_title": "머니 / 혜택",
        "description": "ETF와 산업을 살펴본 기록, 학생 혜택 등 생활 정보를 모았습니다.",
    },
    "생각": {
        "slug": "thoughts",
        "title": "생각 노트: 관심 있는 주제에 대한 개인적인 기록",
        "nav_title": "생각",
        "description": "읽고 관심을 둔 주제에서 공감한 점과 더 생각해 볼 질문을 기록합니다.",
    },
    "CULTURE": {
        "slug": "culture",
        "title": "작품 / 만화 노트: 직접 보고 읽은 리뷰",
        "nav_title": "작품 / 만화",
        "description": "직접 본 드라마와 영화, 읽은 만화의 인상과 기억에 남은 장면을 기록합니다.",
    },
}


def build_hubs(items):
    """게시글과 카탈로그의 카테고리 허브를 만든다."""
    categorized_items = [
        item for item in items if item["type"] in {"post", "catalog"}
    ]
    categories = sorted({
        content_category(item)
        for item in categorized_items
        if content_category(item)
    }, key=str.casefold)
    configured = dict(HUB_CATEGORIES)
    used_slugs = {str(item.get("slug", "")).lower() for item in items}
    for category_label in categories:
        category = category_label.upper()
        if category in configured:
            continue
        normalized = unicodedata.normalize("NFC", category_label.lower())
        slug = re.sub(r"[^a-z0-9가-힣]+", "-", normalized).strip("-") or "notes"
        while slug in used_slugs:
            slug = f"notes-{slug}"
        used_slugs.add(slug)
        display_name = engine_config.CATEGORY_LABELS.get(category, category_label)
        configured[category] = {
            "slug": slug,
            "title": f"{display_name}: {engine_config.SITE_NAME} 콘텐츠 모음",
            "nav_title": display_name,
            "description": f"{engine_config.SITE_NAME}의 {display_name} 카테고리 콘텐츠를 모았습니다.",
        }

    hubs = []
    for category, info in configured.items():
        members = [
            item
            for item in categorized_items
            if content_category(item) == category
        ]
        if not members:
            continue
        rows = "".join(
            f'<li><a href="{content_path(p)}"><strong>{escape(p["title"])}</strong></a>'
            f'<br><span class="related-post-date">{escape(p["updated_date"])}  /  {escape(p["description"])}</span></li>\n'
            for p in members
        )
        hubs.append({
            "slug": info["slug"],
            "type": "hub",
            "category": category,
            "title": info["title"],
            "nav_title": info["nav_title"],
            "description": info["description"],
            "published_date": max(p["published_date"] for p in members),
            "updated_date": max(p["updated_date"] for p in members),
            "badge": f"#{category}",
            "html_content": f"<ul class=\"hub-post-list\">\n{rows}</ul>",
            "toc_tokens": [],
            "meta": {},
        })
    return hubs


def build_category_redirects():
    for old_slug, new_slug in engine_config.CATEGORY_REDIRECTS.items():
        target_url = archive_path(engine_config.CATEGORY_URL_PREFIX, new_slug)
        target_label = engine_config.CATEGORY_LABELS.get(new_slug.upper(), new_slug)
        output_path = engine_config.OUT_DIR / engine_config.CATEGORY_URL_PREFIX.strip("/") / old_slug / "index.html"
        claim_output(output_path, f"category redirect {old_slug}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="robots" content="noindex, follow">
  <link rel="canonical" href={quoteattr(engine_config.SITE_ORIGIN + target_url)}>
  <meta http-equiv="refresh" content={quoteattr(f"0;url={target_url}")}>
  <title>카테고리 이동</title>
</head>
<body>
  <p>카테고리 주소가 변경되었습니다. <a href={quoteattr(target_url)}>{escape(target_label)} 노트로 이동</a></p>
</body>
</html>
""",
            encoding="utf-8",
        )


def build_archive_page(
    tpl_archive, tpl_head, tpl_nav, footer_html, docs_assets, site_domain,
    top_nav_links, title, description, canonical_path, items, output_path,
    pagination="", robots="index, follow",
):
    head_html = render_head(
        tpl_head,
        title=title,
        description=description,
        tags=[],
        canonical_path=canonical_path,
        og_image=f"{engine_config.SITE_ORIGIN}{engine_config.BASE_URL}/assets/og-home.svg",
        robots=robots,
    )
    nav_html = render_nav(tpl_nav, "", top_nav_links)
    archive_entries = [
        {
            "item": item,
            "url": tag_path(item["slug"]) if item["type"] == "tag" else content_path(item),
            "category_label": engine_config.CATEGORY_LABELS.get(
                content_category(item), content_category(item)
            ),
        }
        for item in items
    ]
    archive_fragment = TemplateFragment(
        tpl_archive.environment, "partial_archive_items.html",
        {"archive_entries": archive_entries},
    )
    rendered = tpl_archive.render(
        HEAD_HTML=Markup(head_html),
        NAV_HTML=Markup(nav_html),
        FOOTER_HTML=Markup(footer_html),
        TITLE=title,
        DESCRIPTION=description,
        ITEMS=archive_fragment,
        PAGINATION=Markup(pagination),
        items=items,
        archive_entries=archive_entries,
    )
    claim_output(output_path, f"archive {title} ({canonical_path})")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")


def build_post_archives(content_items, tpl_archive, tpl_head, tpl_nav, footer_html, docs_assets, site_domain, top_nav_links):
    ordered_items = sorted(
        content_items,
        key=lambda item: (item["published_date"], item["slug"]),
        reverse=True,
    )
    page_count = max(1, (len(ordered_items) + engine_config.POSTS_PER_PAGE - 1) // engine_config.POSTS_PER_PAGE)
    archive_paths = []
    for page_number in range(1, page_count + 1):
        slug = "" if page_number == 1 else str(page_number)
        route = archive_path(engine_config.POSTS_URL_PREFIX, slug)
        if page_number == 1:
            archive_paths.append(route)
        page_items = ordered_items[
            (page_number - 1) * engine_config.POSTS_PER_PAGE:page_number * engine_config.POSTS_PER_PAGE
        ]
        pagination_links = []
        if page_number > 1:
            previous_slug = "" if page_number == 2 else str(page_number - 1)
            pagination_links.append(
                f'<a href="{archive_path(engine_config.POSTS_URL_PREFIX, previous_slug)}">← 이전</a>'
            )
        if page_number < page_count:
            pagination_links.append(
                f'<a href="{archive_path(engine_config.POSTS_URL_PREFIX, str(page_number + 1))}">다음 →</a>'
            )
        output_path = engine_config.OUT_DIR / engine_config.POSTS_URL_PREFIX.strip("/")
        if slug:
            output_path /= slug
        output_path /= "index.html"
        build_archive_page(
            tpl_archive, tpl_head, tpl_nav, footer_html, docs_assets,
            site_domain, top_nav_links,
            "콘텐츠 목록" if page_number == 1 else f"콘텐츠 목록 {page_number}페이지",
            engine_config.SITE_DESCRIPTION,
            route,
            page_items,
            output_path,
            "".join(pagination_links),
            robots="index, follow" if page_number == 1 else "noindex, follow",
        )
    return archive_paths


def build_category_index(hubs, tpl_archive, tpl_head, tpl_nav, footer_html, docs_assets, site_domain, top_nav_links):
    route = archive_path(engine_config.CATEGORY_URL_PREFIX)
    output_path = engine_config.OUT_DIR / engine_config.CATEGORY_URL_PREFIX.strip("/") / "index.html"
    build_archive_page(
        tpl_archive, tpl_head, tpl_nav, footer_html, docs_assets,
        site_domain, top_nav_links,
        "카테고리",
        f"{engine_config.SITE_NAME}의 기술 기록을 주제별 카테고리로 모았습니다.",
        route,
        hubs,
        output_path,
    )
    return route


def build_tag_archives(posts, tpl_archive, tpl_head, tpl_nav, footer_html, docs_assets, site_domain, top_nav_links):
    grouped_tags = {}
    for post in posts:
        for raw_tag in post.get("tags", []):
            tag = raw_tag.strip()
            if not tag:
                continue
            key = tag.casefold()
            grouped_tags.setdefault(key, {"label": tag, "posts": []})["posts"].append(post)

    tags_by_base = {}
    for key, entry in grouped_tags.items():
        label = entry["label"]
        base = re.sub(r"[^a-z0-9._-]+", "-", label.casefold()).strip("-")
        base = base or quote(label.casefold(), safe="-._~")
        tags_by_base.setdefault(base, []).append((key, label))

    tag_slugs = {}
    for base, entries in tags_by_base.items():
        primary = next(
            (key for key, label in entries if label.casefold() == base),
            entries[0][0],
        )
        for key, label in entries:
            if key == primary:
                tag_slugs[key] = base
            else:
                suffix = hashlib.sha1(key.encode("utf-8")).hexdigest()[:8]
                tag_slugs[key] = f"{base}--{suffix}"

    for key, entry in grouped_tags.items():
        for post in entry["posts"]:
            post.setdefault("tag_routes", []).append((tag_slugs[key], entry["label"]))

    index_items = []
    for key, entry in sorted(
        grouped_tags.items(),
        key=lambda pair: pair[1]["label"].casefold(),
    ):
        slug = tag_slugs[key]
        posts_for_tag = sorted(
            entry["posts"],
            key=lambda item: (item["published_date"], item["slug"]),
            reverse=True,
        )
        tag_item = {
            "slug": slug,
            "type": "tag",
            "title": f"태그: {entry['label']}",
            "description": f"{entry['label']} 태그가 포함된 글 {len(posts_for_tag)}개",
            "published_date": "",
        }
        route = tag_path(slug)
        build_archive_page(
            tpl_archive, tpl_head, tpl_nav, footer_html, docs_assets,
            site_domain, top_nav_links,
            tag_item["title"], tag_item["description"], route,
            posts_for_tag,
            tag_output_path(slug),
            robots="noindex, follow",
        )
        index_items.append({
            "slug": slug,
            "type": "tag",
            "title": entry["label"],
            "description": f"{len(posts_for_tag)}개 글",
            "published_date": "",
        })

    tag_index_path = archive_path(engine_config.TAG_URL_PREFIX)
    build_archive_page(
        tpl_archive, tpl_head, tpl_nav, footer_html, docs_assets,
        site_domain, top_nav_links,
        "태그 목록",
        "태그별로 관련 글을 찾아볼 수 있습니다.",
        tag_index_path,
        index_items,
        engine_config.OUT_DIR / engine_config.TAG_URL_PREFIX.strip("/") / "index.html",
        robots="noindex, follow",
    )
    return len(grouped_tags)


def display_category_label(category):
    category_name = str(category or "NOTE")
    return engine_config.CATEGORY_LABELS.get(category_name.upper(), category_name)


def render_related_posts(posts, hubs, category=None, exclude_slug=None, limit=3, heading="이어서 읽기 좋은 노트"):
    """같은 카테고리를 우선해 관련 글을 고르고, 허브가 있으면 전체 보기 링크를 붙인다."""
    candidates = [p for p in posts if p["slug"] != exclude_slug]
    same = [p for p in candidates if category and str(p.get("meta", {}).get("category", "")).upper() == category.upper()]
    picked = (same + [p for p in candidates if p not in same])[:limit]
    if not picked:
        return ""
    rows = "".join(
        f'<a class="related-post-item" href="{content_path(p)}">'
        f'<span class="related-post-cat">[{escape(display_category_label(p.get("meta", {}).get("category")))}]</span>'
        f'<span class="related-post-title">{escape(p["title"])}</span>'
        f'<span class="related-post-date">{escape(p["updated_date"])}</span></a>'
        for p in picked
    )
    hub = next((h for h in hubs if category and h["category"] == category.upper()), None)
    hub_link = (
        f'<a class="related-post-more" href="{content_path(hub)}">{escape(hub["nav_title"])} 전체 보기 →</a>'
        if hub else ""
    )
    return f"""
    <aside class="related-posts-box" aria-label="관련 글">
      <h2 class="related-posts-title">{escape(heading)}</h2>
      <div class="related-post-list">{rows}</div>
      {hub_link}
    </aside>
    """


def render_ad_block():
    ad_html = render_ad(engine_config.AD_SLOT_MID, ad_format="auto", full_width_responsive=True)
    if not ad_html:
        return ""
    return f'<div class="post-inline-ad" aria-label="광고"><span>광고</span>{ad_html}</div>'


def insert_inline_ad(html, min_sections=3):
    """글자 수에 비례해 본문 광고 개수를 정하고, 본문 길이를 고르게 나누는 h2 앞에 배치한다."""
    marks = [m.start() for m in re.finditer(r"<h2[ >]", html)][1:]
    text_len = len(re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", html)))
    count = min(engine_config.INLINE_AD_MAX, text_len // engine_config.INLINE_AD_CHARS, len(marks))
    if len(marks) + 1 < min_sections or count < 1:
        return html
    html_len = len(html)
    chosen = []
    for k in range(1, count + 1):
        target = html_len * k / (count + 1)
        best = min((m for m in marks if m not in chosen), key=lambda m: abs(m - target), default=None)
        if best is not None:
            chosen.append(best)
    ad = render_ad_block()
    for pos in sorted(chosen, reverse=True):
        html = html[:pos] + ad + html[pos:]
    return html


def render_author_box(category=None):
    note = engine_config.AUTHOR_NOTES.get(str(category or "").upper(), engine_config.AUTHOR_NOTE_DEFAULT)
    return f"""
    <aside class="author-box" aria-label="글쓴이 소개">
      <div class="author-box-copy">
        <span class="author-box-name">{escape(engine_config.AUTHOR_NAME)}</span>
        <p>{escape(engine_config.AUTHOR_BIO)}</p>
        <p class="author-box-note">{escape(note)}</p>
      </div>
    </aside>
    """


def build_post(item, catalog_nav_list, category_nav_list, tpl_post, tpl_head, tpl_nav, footer_html, docs_assets, site_domain, posts=(), hubs=(), top_nav_links=""):
    meta = item.get("meta", {})
    slug = item["slug"]
    title = item["title"]
    description = item["description"]
    og_filename = f"og-{slug}.svg"

    generate_page_og_image(docs_assets, og_filename, item["badge"], title, site_domain, f"OG image for {item.get('source_path', f'category {slug}')}")
    head_html = render_head(
        tpl_head,
        title=title,
        description=description,
        tags=item.get("tags", []),
        canonical_path=content_path(item),
        og_image=f"{engine_config.SITE_ORIGIN}{engine_config.BASE_URL}/assets/{og_filename}",
        og_type="article"
    )
    nav_html = render_nav(
        tpl_nav,
        f'<a href="{site_root_path()}" class="nav-back-link">← 전체 홈</a>',
        top_nav_links,
    )
    toc_tokens = item.get("toc_tokens", [])
    post_headings = []

    def append_headings(tokens):
        for token in tokens:
            post_headings.append(token)
            append_headings(token.get("children", []))

    append_headings(toc_tokens)
    toc_items = []
    post_headings = [heading for heading in post_headings if heading.get("level", 0) >= 2]
    for index, heading in enumerate(post_headings, start=1):
        name = heading["name"]
        prefix, separator, remainder = name.partition(". ")
        if separator and prefix.isdecimal():
            name = remainder
        toc_items.append(
            f'<li><a href={quoteattr("#" + heading["id"])}>'
            f'{index:02d}. {escape(name)}</a></li>\n'
        )
    toc_items = "".join(toc_items)
    content_html = item["html_content"]
    json_ld = ""
    byline = ""
    post_meta = ""
    top_ad_block = f"""
    <div class="journal-masthead-wrap">
      <div class="top-leaderboard-ad" aria-label="상단 광고">
        {render_ad(engine_config.AD_SLOT_TOP, ad_format="horizontal", full_width_responsive=True)}
      </div>
    </div>
    """
    side_ad_block = f'<div class="sidebar-ad-box">{render_ad(engine_config.AD_SLOT_SIDE)}</div>'
    if item["type"] == "post":
        content_html = insert_inline_ad(content_html)
        content_html += render_ad_block()
        content_html += render_author_box(meta.get("category"))
        content_html += render_related_posts(posts, hubs, meta.get("category"), exclude_slug=slug)
        byline = f'<span class="post-byline">글 {escape(engine_config.AUTHOR_NAME)}</span>'
        plain_text = re.sub(r"<[^>]+>", " ", item["html_content"])
        reading_minutes = max(1, round(len(re.sub(r"\s+", "", plain_text)) / 500))
        category = escape(display_category_label(meta.get("category")))
        tag_links = " ".join(
            f'<a href="{tag_path(tag_slug)}">{escape(tag_label)}</a>'
            for tag_slug, tag_label in item.get("tag_routes", [])
        )
        post_meta = f"""
        <div class="catalog-meta-bar post-meta-bar" aria-label="글 정보">
          <span class="post-meta-category">{category}</span>
          <span>발행일: {escape(item["published_date"])}</span>
          <span>예상 읽기 시간: 약 {reading_minutes}분</span>
          <span>작성: {escape(engine_config.AUTHOR_NAME)}</span>
          <span class="post-tags">{tag_links}</span>
        </div>
        """
        ld = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title,
            "description": description,
            "datePublished": item["published_date"],
            "dateModified": item["updated_date"],
            "author": {"@type": "Person", "name": engine_config.AUTHOR_NAME},
            "mainEntityOfPage": f"{engine_config.SITE_ORIGIN}{content_path(item)}",
        }
        json_ld = '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>"
    elif item["type"] == "page":
        top_ad_block = ""
        side_ad_block = ""
    rendered = tpl_post.render(
        JSON_LD=Markup(json_ld),
        BYLINE=Markup(byline),
        HEAD_HTML=Markup(head_html),
        NAV_HTML=Markup(nav_html),
        FOOTER_HTML=Markup(footer_html),
        TOP_AD_BLOCK=Markup(top_ad_block),
        SIDE_AD_BLOCK=Markup(side_ad_block),
        CAT_NAV_LINKS=Markup(catalog_nav_list),
        TOC_ITEMS=Markup(toc_items),
        BADGE=item["badge"],
        DATE=item["updated_date"],
        TITLE=title,
        DESCRIPTION=description,
        POST_META=Markup(post_meta),
        CONTENT_HTML=Markup(content_html),
        CATEGORY_NAV_LINKS=Markup(category_nav_list),
        AD_SIDE=Markup(""),
        page=item,
    )

    output_path = content_output_path(item)
    claim_output(output_path, str(item.get("source_path", f"category {slug}")))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    print(f"[OK] {output_path.relative_to(engine_config.OUT_DIR)} 생성 완료")

def build(config: BuildConfig):
    from .config import use_config

    workspace = Path(tempfile.mkdtemp(prefix=".naru-build-", dir=config.output_dir.parent))
    staged_output = workspace / "output"
    backup = workspace / "previous"
    clean_workspace = True
    token = CSS_VERSION.set("")
    try:
        if config.output_dir.exists():
            for path in config.output_dir.rglob("*"):
                if path.is_symlink():
                    raise ValueError(f"{path}: symlinks in the output directory are not supported")
            shutil.copytree(config.output_dir, staged_output)
        else:
            staged_output.mkdir()
        staged_config = BuildConfig(
            config.site_root, staged_output, config.settings,
            config.include_drafts, config.include_future,
        )
        with use_config(staged_config), track_output_paths():
            try:
                completion_message = _build(staged_config)
            except TemplateError as error:
                frames = traceback.extract_tb(error.__traceback__)
                template_frame = next(
                    (frame for frame in reversed(frames) if frame.filename.endswith(".html")),
                    None,
                )
                filename = getattr(error, "filename", None) or (
                    template_frame.filename if template_frame else getattr(error, "name", None)
                )
                line = getattr(error, "lineno", None) or (
                    template_frame.lineno if template_frame else None
                )
                location = str(filename or "template")
                if line:
                    location += f":{line}"
                raise ValueError(f"{location}: template error: {error}") from error
        if config.output_dir.exists():
            config.output_dir.rename(backup)
        try:
            staged_output.rename(config.output_dir)
        except OSError as error:
            if backup.exists():
                try:
                    backup.rename(config.output_dir)
                except OSError as rollback_error:
                    clean_workspace = False
                    raise OSError(
                        f"cannot replace output; previous output is at {backup}: "
                        f"{rollback_error}"
                    ) from error
            raise
        print(completion_message)
    finally:
        CSS_VERSION.reset(token)
        if clean_workspace:
            shutil.rmtree(workspace)


def _build(config: BuildConfig):
    pages_dir = engine_config.BASE_DIR / "content" / "pages"
    items = load_all_contents(
        engine_config.DATA_DIR, engine_config.POSTS_DIR, pages_dir,
        include_drafts=config.include_drafts, include_future=config.include_future,
    )
    claim_output(engine_config.OUT_DIR / ".naru-output", "Naru output marker")
    register_source_outputs()
    templates = create_template_environment(config.settings)
    tpl_home = templates.get_template("template_index.html")
    tpl_cat = templates.get_template("template_catalog.html")
    tpl_post = templates.get_template("template_post.html")
    tpl_archive = templates.get_template("template_archive.html")
    tpl_head = templates.get_template("partial_head.html")
    tpl_nav = templates.get_template("partial_nav.html")
    tpl_footer = templates.get_template("partial_footer.html")
    pending = [
        "template_index.html", "template_catalog.html", "template_post.html",
        "template_archive.html", "partial_head.html", "partial_nav.html",
        "partial_footer.html", "partial_googletag.html", "partial_catalog_entries.html",
    ]
    checked = set()
    while pending:
        name = pending.pop()
        if name in checked:
            continue
        checked.add(name)
        try:
            source, filename, _ = templates.loader.get_source(templates, name)
        except TemplateNotFound:
            continue
        parsed = templates.parse(source, name=name, filename=filename)
        pending.extend(
            reference for reference in meta.find_referenced_templates(parsed)
            if reference is not None
        )

    engine_config.OUT_DIR.mkdir(parents=True, exist_ok=True)
    clean_generated_pages()
    clean_post_images()
    docs_assets = engine_config.OUT_DIR / "assets"
    if (engine_config.BASE_DIR / "assets").exists():
        if docs_assets.exists():
            shutil.rmtree(docs_assets)
        shutil.copytree(engine_config.BASE_DIR / "assets", docs_assets)

    sync_static_files()
    docs_assets.mkdir(parents=True, exist_ok=True)
    if not (engine_config.TPL_DIR / "partial_head.html").exists() and not any(
        path.exists()
        for path in (
            engine_config.BASE_DIR / "assets" / "naru.css",
            engine_config.STATIC_DIR / "assets" / "naru.css",
        )
    ):
        css = files("naru").joinpath("defaults", "naru.css").read_text(
            encoding="utf-8"
        )
        claim_output(docs_assets / "naru.css", "default stylesheet")
        (docs_assets / "naru.css").write_text(css, encoding="utf-8")
    stylesheet = docs_assets / "naru.css"
    if stylesheet.is_file():
        CSS_VERSION.set(hashlib.sha256(stylesheet.read_bytes()).hexdigest()[:12])
    theme_stylesheet = docs_assets / "naru-theme.css"
    claim_output(theme_stylesheet, "theme stylesheet")
    theme_stylesheet.write_text(theme_css(config.settings["theme"]), encoding="utf-8")
    theme_stylesheets = []
    for relative in ["assets/naru-theme.css", *config.settings["theme"]["custom_css"]]:
        stylesheet = engine_config.OUT_DIR / relative
        version = hashlib.sha256(stylesheet.read_bytes()).hexdigest()[:12]
        theme_stylesheets.append(
            f"{engine_config.BASE_URL}/{quote(relative, safe='/')}?v={version}"
        )
    templates.globals["THEME_STYLESHEETS"] = theme_stylesheets
    site_domain = generate_github_pages_meta()

    sync_post_images(items, docs_assets)

    all_catalogs = [item for item in items if item["type"] == "catalog"]
    ordered_catalogs = sorted(all_catalogs, key=content_sort_key, reverse=True)

    nav_li_list = []
    for item in ordered_catalogs:
        short_date = item.get("updated_date", "")[5:].replace("-", ".")
        date_span = f' <span class="sidebar-date">{short_date}</span>' if short_date else ""
        nav_li_list.append(
            f'<li><a href="{content_path(item)}">{escape(item["nav_title"])}{date_span}</a></li>\n'
        )

    catalog_nav_list = "".join(nav_li_list)
    hubs = build_hubs(items)
    top_nav_links = render_category_group_links("nav-group")
    nav_html = render_nav(tpl_nav, "", top_nav_links)
    info_pages = [item for item in items if item["type"] == "page"]
    footer_html = render_footer(tpl_footer, site_domain, info_pages)
    if (engine_config.STATIC_DIR / "tools").exists():
        build_tools_page(nav_html, footer_html)

    all_posts = [it for it in items if it["type"] == "post"]
    categorized_items = [
        item for item in items if item["type"] in {"post", "catalog"}
    ]
    category_nav_items = [
        f'<li><a href="{site_root_path()}">🏠 전체 콘텐츠</a></li>'
    ]
    for hub in hubs:
        count = sum(
            content_category(item) == hub["category"]
            for item in categorized_items
        )
        category_nav_items.append(
            f'<li><a href="{content_path(hub)}">{escape(hub["nav_title"])}'
            f' <span class="sidebar-count">{count}</span></a></li>'
        )
    category_nav_list = "".join(category_nav_items)

    archive_paths = [build_category_index(
        hubs, tpl_archive, tpl_head, tpl_nav, footer_html, docs_assets,
        site_domain, top_nav_links,
    )]
    if (engine_config.OUT_DIR / "tools" / "index.html").is_file():
        archive_paths.append(archive_path("tools"))
    if (engine_config.OUT_DIR / "tools" / "regex-live-tester" / "index.html").is_file():
        archive_paths.append(archive_path("tools/regex-live-tester"))
    archive_paths.extend(build_post_archives(
        categorized_items, tpl_archive, tpl_head, tpl_nav, footer_html, docs_assets,
        site_domain, top_nav_links,
    ))
    tag_count = build_tag_archives(
        all_posts, tpl_archive, tpl_head, tpl_nav, footer_html, docs_assets,
        site_domain, top_nav_links,
    )

    build_home(items, tpl_home, tpl_head, tpl_nav, footer_html, docs_assets, site_domain, top_nav_links, hubs)

    for it in items:
        if it["type"] == "catalog":
            build_catalog(it, catalog_nav_list, category_nav_list, tpl_cat, tpl_head, tpl_nav, footer_html, docs_assets, site_domain, all_posts, hubs, top_nav_links)
        elif it["type"] == "post":
            build_post(it, catalog_nav_list, category_nav_list, tpl_post, tpl_head, tpl_nav, footer_html, docs_assets, site_domain, all_posts, hubs, top_nav_links)
        elif it["type"] == "page":
            build_post(it, catalog_nav_list, category_nav_list, tpl_post, tpl_head, tpl_nav, footer_html, docs_assets, site_domain, top_nav_links=top_nav_links)

    for hub in hubs:
        build_post(hub, catalog_nav_list, category_nav_list, tpl_post, tpl_head, tpl_nav, footer_html, docs_assets, site_domain, all_posts, hubs, top_nav_links)

    build_category_redirects()
    warn_broken_fragments(items)
    generate_sitemap(items + hubs, archive_paths)
    generate_rss([item for item in items if item["type"] != "page"])
    generate_robots()

    return (
        f"\n[DONE] [{site_domain}] 사이트 빌드 완료! "
        f"(총 {len(items)}개 콘텐츠, 태그 아카이브 {tag_count}개)"
    )
