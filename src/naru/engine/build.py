import hashlib
import json
import re
import shutil
from urllib.parse import quote
from xml.sax.saxutils import escape, quoteattr

from .ads import render_ad, render_infeed_ad
from .config import (
    AD_SLOT_MID,
    AD_SLOT_SIDE,
    AD_SLOT_TOP,
    ADSENSE_PUB_ID,
    AUTHOR_BIO,
    AUTHOR_NAME,
    AUTHOR_NOTE_DEFAULT,
    AUTHOR_NOTES,
    BASE_DIR,
    BASE_URL,
    CATEGORY_LABELS,
    CATEGORY_REDIRECTS,
    CATEGORY_URL_PREFIX,
    DATA_DIR,
    HOME_CATEGORY_GROUPS,
    HOME_CATEGORY_ORDER,
    HOME_MAX_ADS,
    HOME_POSTS_PER_CATEGORY,
    HOME_RECENT_POSTS,
    INLINE_AD_CHARS,
    INLINE_AD_MAX,
    OUT_DIR,
    POSTS_DIR,
    POSTS_PER_PAGE,
    POSTS_URL_PREFIX,
    SITE_DESCRIPTION,
    SITE_NAME,
    SITE_ORIGIN,
    SITE_SLOGAN_EN,
    SITE_SLOGAN_KO,
    SITE_TAGLINE,
    STATIC_DIR,
    TAG_URL_PREFIX,
    TPL_DIR,
)
from .loader import load_all_contents
from .metadata import content_sort_key, keyword_content
from .routes import (
    archive_path,
    content_output_path,
    content_path,
    site_root_path,
    tag_output_path,
    tag_path,
)
from .seo import (
    generate_github_pages_meta,
    generate_page_og_image,
    generate_robots,
    generate_rss,
    generate_sitemap,
)


def sync_static_files():
    """static/ 폴더 내 파일들을 docs/ 루트로 그대로 복사"""
    if not STATIC_DIR.exists():
        STATIC_DIR.mkdir(parents=True, exist_ok=True)
        return

    copied_count = 0
    for item in STATIC_DIR.iterdir():
        dest = OUT_DIR / item.name
        if item.is_file():
            shutil.copy2(item, dest)
            copied_count += 1
        elif item.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)
            copied_count += 1
    print(f"[OK] static/ 파일 동기화 완료 ({copied_count}개)")


def clean_generated_pages():
    """이전 경로의 페이지가 새 빌드 결과에 남지 않도록 HTML 산출물만 제거"""
    removed_count = 0
    for page in OUT_DIR.rglob("*.html"):
        page.unlink()
        removed_count += 1
    print(f"[OK] 이전 HTML 산출물 정리 완료 ({removed_count}개)")


def sync_post_images(items, docs_assets):
    copied_count = 0
    for item in items:
        for source, relative_dest in item.get("local_image_assets", []):
            destination = docs_assets / relative_dest
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            copied_count += 1
    print(f"[OK] 게시물 이미지 동기화 완료 ({copied_count}개)")

def read_template(name: str) -> str:
    return (TPL_DIR / name).read_text(encoding="utf-8")

def render_head(
    tpl_head, title, description, tags, canonical_path, og_image,
    og_type="website", robots="index, follow",
):
    return tpl_head.replace("{{ BASE_URL }}", BASE_URL) \
                   .replace("{{ SITE_ORIGIN }}", SITE_ORIGIN) \
                   .replace("{{ SITE_NAME }}", escape(SITE_NAME)) \
                   .replace("{{ ADSENSE_PUB_ID }}", ADSENSE_PUB_ID) \
                   .replace("{{ TITLE }}", escape(title)) \
                   .replace("{{ DESCRIPTION }}", escape(description)) \
                   .replace("{{ KEYWORDS }}", escape(keyword_content(tags))) \
                   .replace("{{ CANONICAL_PATH }}", canonical_path) \
                   .replace("{{ OG_IMAGE }}", og_image) \
                   .replace("{{ OG_TYPE }}", og_type) \
                   .replace("{{ ROBOTS }}", robots)

def render_nav(tpl_nav, nav_right_html, top_nav_links):
    return tpl_nav.replace("{{ BASE_URL }}", BASE_URL) \
                  .replace("{{ SITE_NAME }}", escape(SITE_NAME)) \
                  .replace("{{ SITE_TAGLINE }}", escape(SITE_TAGLINE)) \
                  .replace("{{ TOP_NAV_LINKS }}", top_nav_links) \
                  .replace("{{ NAV_RIGHT }}", nav_right_html)

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
    for label, _, _, icon_name in HOME_CATEGORY_GROUPS:
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
    return tpl_footer.replace("{{ BASE_URL }}", BASE_URL) \
                     .replace("{{ SITE_NAME }}", escape(SITE_NAME)) \
                     .replace("{{ SITE_TAGLINE }}", escape(SITE_TAGLINE)) \
                     .replace("{{ AUTHOR_NAME }}", escape(AUTHOR_NAME)) \
                     .replace("{{ SITE_DOMAIN }}", site_domain) \
                     .replace("{{ FOOTER_GROUP_LINKS }}", render_category_group_links("footer-group")) \
                     .replace("{{ FOOTER_INFO_LINKS }}", info_links)

def build_tools_page(nav_html, footer_html):
    source_path = STATIC_DIR / "tools" / "index.html"
    output_path = OUT_DIR / "tools" / "index.html"
    rendered = source_path.read_text(encoding="utf-8") \
                          .replace("{{ NAV_HTML }}", nav_html) \
                          .replace("{{ FOOTER_HTML }}", footer_html)
    if "{{ NAV_HTML }}" in rendered or "{{ FOOTER_HTML }}" in rendered:
        raise ValueError(f"{source_path}: shared navigation or footer placeholder was not rendered")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    print(f"[OK] {output_path.relative_to(OUT_DIR)} 공통 헤더/푸터 적용 완료")

def build_home(items, tpl_home, tpl_head, tpl_nav, footer_html, docs_assets, site_domain, top_nav_links, hubs):
    title = SITE_TAGLINE
    description = SITE_DESCRIPTION
    og_filename = "og-home.svg"
    generate_page_og_image(docs_assets, og_filename, SITE_NAME, title, site_domain)

    head_html = render_head(
        tpl_head,
        title=title,
        description=description,
        tags=[SITE_NAME, "기술 기록", "IT", "문화", "스포츠"],
        canonical_path=site_root_path(),
        og_image=f"{SITE_ORIGIN}{BASE_URL}/assets/{og_filename}"
    )

    articles = [item for item in items if item["type"] == "post"]
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
        category = str(item.get("meta", {}).get("category", "NOTE")).upper()
        grouped_articles.setdefault(category, []).append(item)

    category_order = [str(category).strip().upper() for category in HOME_CATEGORY_ORDER]
    ordered_categories = [category for category in category_order if category in grouped_articles]
    ordered_categories.extend(sorted(set(grouped_articles) - set(ordered_categories)))
    hubs_by_category = {hub["category"].upper(): hub for hub in hubs}
    category_sections = {}
    # 카드가 충분한 카테고리 중 하나 걸러 한 곳씩, 최대 HOME_MAX_ADS개만 광고를 넣는다
    ad_candidates = [c for c in ordered_categories if len(grouped_articles[c]) > 5]
    ad_categories = set((ad_candidates[1::2] or ad_candidates[:1])[:HOME_MAX_ADS])
    for category in ordered_categories:
        category_articles = sorted(
            grouped_articles[category],
            key=lambda item: item.get("updated_date", ""),
            reverse=True,
        )
        visible_articles = category_articles[:HOME_POSTS_PER_CATEGORY]
        cards = []
        for article_index, item in enumerate(visible_articles, start=1):
            date_short = escape(item.get("updated_date", ""))[5:]
            cards.append(f"""
              <a class="home-article-card" href="{content_path(item)}">
                <span class="home-article-date">{date_short}</span>
                <strong>{escape(item["title"])}</strong>
                <span class="home-article-description">{escape(item["description"])}</span>
              </a>""")
            if category in ad_categories and article_index == 4 and article_index < len(visible_articles):
                cards.append(f"""
              <div class="home-infeed-ad" aria-label="광고">
                <span>광고</span>
                {render_infeed_ad(AD_SLOT_MID)}
              </div>""")
        label = CATEGORY_LABELS.get(category, category)
        hub = hubs_by_category.get(category)
        more_link = ""
        if len(category_articles) >= HOME_POSTS_PER_CATEGORY and hub:
            more_link = (
                f'<a class="home-category-more" href="{content_path(hub)}">'
                f'더 보기 <span>({len(category_articles)}개 글)</span> →</a>'
            )
        category_sections[category] = f"""
        <section class="home-article-category" aria-label="{escape(label)} 글">
          <div class="home-category-heading">
            <h2>{escape(label)}</h2>
            <span>{len(category_articles):02d} POSTS</span>
          </div>
          <div class="home-article-grid">{"".join(cards)}
          </div>
          {more_link}
        </section>"""

    recent_items = sorted(articles, key=lambda item: item.get("updated_date", ""), reverse=True)[:HOME_RECENT_POSTS]
    recent_rows = "".join(f"""
          <li><a href="{content_path(item)}">
            <span class="home-recent-date">{escape(item.get("updated_date", ""))[5:]}</span>
            <strong>{escape(item["title"])}</strong>
          </a></li>""" for item in recent_items)
    recent_posts_html = f"""<aside class="home-recent" aria-label="최근 글">
        <div class="home-category-heading"><h2>최근 글</h2><span>LATEST</span></div>
        <ul class="home-recent-list">{recent_rows}
        </ul>
      </aside>""" if recent_items else ""

    configured_categories = {
        category
        for _, _, categories, _ in HOME_CATEGORY_GROUPS
        for category in categories
    }
    category_groups = list(HOME_CATEGORY_GROUPS)
    ungrouped_categories = sorted(set(category_sections) - configured_categories)
    if ungrouped_categories:
        category_groups.append(("기타", "MORE NOTES", tuple(ungrouped_categories), "spark"))

    grouped_sections = []
    for group_label, group_kicker, group_categories, icon_name in category_groups:
        available_categories = [
            category for category in group_categories if category in category_sections
        ]
        if not available_categories:
            continue
        group_count = sum(len(grouped_articles[category]) for category in available_categories)
        icon_svg = home_group_icon(icon_name)
        utility_link = ""
        if group_label == "유틸리티":
            utility_link = f"""
            <a class="home-utility-launch" href="{BASE_URL}/tools/">
              <span class="home-utility-mark">{icon_svg}</span>
              <span class="home-utility-copy">
                <strong>브라우저 도구 바로 열기</strong>
                <small>정규식, 변환, 네트워크 계산과 패킷 명령어를 한곳에서 확인합니다.</small>
              </span>
              <span class="home-utility-action">도구 열기 <span aria-hidden="true">→</span></span>
            </a>"""
        grouped_sections.append(f"""
        <section class="home-category-group" aria-labelledby="home-group-{icon_name}">
          <div class="home-group-heading">
            <span class="home-group-icon">{icon_svg}</span>
            <div class="home-group-title">
              <span class="home-group-kicker">{escape(group_kicker)}</span>
              <h2 id="home-group-{icon_name}">{escape(group_label)}</h2>
            </div>
            <span class="home-group-count">{group_count:02d} POSTS</span>
          </div>
          {utility_link}
          <div class="home-group-categories">
            {"".join(category_sections[category] for category in available_categories)}
          </div>
        </section>""")

    home_content_sections_html = f"""
        <div class="home-article-sections" aria-label="주제별 글 목록">
          {"".join(grouped_sections)}
        </div>"""

    rendered = tpl_home.replace("{{ HEAD_HTML }}", head_html) \
                       .replace("{{ NAV_HTML }}", nav_html) \
                       .replace("{{ QUICK_MENU }}", "") \
                       .replace("{{ TOPIC_LINKS }}", "") \
                       .replace("{{ FOOTER_HTML }}", footer_html) \
                       .replace("{{ BASE_URL }}", BASE_URL) \
                       .replace("{{ SLOGAN_EN_PLAIN }}", escape(SITE_SLOGAN_EN)) \
                       .replace("{{ SLOGAN_EN }}", re.sub(r"\b(Dev|B|J)", r'<span class="slogan-initial">\1</span>', escape(SITE_SLOGAN_EN).replace(" Just", "<br>Just"), count=3)) \
                       .replace("{{ SLOGAN_KO }}", escape(SITE_SLOGAN_KO)) \
                       .replace("{{ RECENT_POSTS }}", recent_posts_html) \
                       .replace("{{ HOME_CONTENT_SECTIONS }}", home_content_sections_html)
    rendered = "\n".join(line.rstrip() for line in rendered.splitlines()) + "\n"

    (OUT_DIR / "index.html").write_text(rendered, encoding="utf-8")
    print("[OK] docs/index.html 생성 완료 (통합 상단바 + 대시보드형 2열 보드)")

def build_catalog(item, nav_items_list, category_nav_list, tpl_cat, tpl_head, tpl_nav, footer_html, docs_assets, site_domain, posts=(), hubs=(), top_nav_links=""):
    code = item["slug"]
    data = item["raw_data"]
    p_info = data.get("page_info", {})
    sites = data.get("sites", [])

    og_filename = f"og-{code}.svg"
    generate_page_og_image(docs_assets, og_filename, f"#{code}", p_info.get("title", f"디렉토리 {code}"), site_domain)

    published_date = item["published_date"]
    updated_date = item["updated_date"]
    links_checked_date = item["links_checked_date"]
    catalog_schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": p_info.get("title", ""),
        "description": p_info.get("description", ""),
        "url": f"{SITE_ORIGIN}{content_path(item)}",
        "datePublished": published_date,
        "dateModified": updated_date,
        "isPartOf": {
            "@type": "WebSite",
            "name": SITE_NAME,
            "url": f"{SITE_ORIGIN}{site_root_path()}",
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
        og_image=f"{SITE_ORIGIN}{BASE_URL}/assets/{og_filename}",
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

    raw_guide = p_info.get("intro_guide", [])
    if isinstance(raw_guide, str):
        paragraphs = [p.strip() for p in raw_guide.split("\n\n") if p.strip()]
    else:
        paragraphs = [str(p).strip() for p in raw_guide if str(p).strip()]

    intro_guide_html = ""
    if paragraphs:
        rendered_blocks = []
        for p in paragraphs:
            if p.startswith("■"):
                lines = p.split("\n", 1)
                heading = lines[0].replace("■", "").strip()
                body = lines[1].strip() if len(lines) > 1 else ""

                if "원리" in heading or "법적" in heading or "주의사항" in heading:
                    rendered_blocks.append(f"""
                    <div class="guide-box-legal">
                      <h3 class="guide-subheading">🛡️ {escape(heading)}</h3>
                      <p>{escape(body)}</p>
                    </div>""")
                elif "오류" in heading or "해결" in heading or "팁" in heading:
                    rendered_blocks.append(f"""
                    <div class="guide-box-tip">
                      <h3 class="guide-subheading">💡 {escape(heading)}</h3>
                      <p>{escape(body)}</p>
                    </div>""")
                else:
                    rendered_blocks.append(f"""
                    <div class="guide-box-normal">
                      <h3 class="guide-subheading">{escape(heading)}</h3>
                      <p>{escape(body)}</p>
                    </div>""")
            else:
                rendered_blocks.append(f'<p class="guide-lead-text">{escape(p)}</p>')

        intro_guide_html = f"""
        <section class="catalog-guide-section" aria-label="이용 안내 및 가이드">
          {"".join(rendered_blocks)}
        </section>"""

    entries = []

    for i, s in enumerate(sites):
        name = s.get("name", "")
        url = s.get("url", "")
        desc = s.get("description", "")
        status = s.get("status", "unknown")
        external_href = quoteattr(url)
        external_target = ' target="_blank" rel="noopener noreferrer"'

        if status == "active":
            status_badge = '<span class="status-active">🟢 접속원활</span>'
        elif status in ("error", "inactive"):
            status_badge = '<span class="status-error">🔴 점검/오류</span>'
        else:
            status_badge = '<span class="status-unverified">⚪ 확인 필요</span>'

        entry = f"""
        <tr class="site-table-row" id="sec-{s.get('id')}">
          <td class="col-rank">{i+1}</td>
          <td class="col-name">{escape(name)}</td>
          <td class="col-url-action">
            <div class="site-link-details">
              <span class="url-text">{escape(url)}</span>
              {f'<p class="site-entry-desc">{escape(desc)}</p>' if desc else ''}
            </div>
            <a href={external_href}{external_target} class="btn-connect" aria-label="{escape(name)} 외부 사이트 열기" title="외부 사이트 열기">
              <svg aria-hidden="true" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3h7v7"/><path d="M10 14 21 3"/><path d="M21 14v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h6"/></svg>
            </a>
          </td>
          <td class="col-status">{status_badge}</td>
        </tr>"""
        entries.append(entry)

        if i == 2 or i == 5:
            entries.append(f'<tr class="ad-row"><td colspan="4"><div class="ad-in-table">{render_ad(AD_SLOT_MID)}</div></td></tr>')

    rendered_cat = tpl_cat.replace("{{ HEAD_HTML }}", head_html) \
                          .replace("{{ NAV_HTML }}", nav_html) \
                          .replace("{{ FOOTER_HTML }}", footer_html) \
                          .replace("{{ TITLE }}", escape(p_info.get("title", ""))) \
                          .replace("{{ DESCRIPTION }}", escape(item["description"])) \
                          .replace("{{ PUBLISHED_DATE }}", published_date) \
                          .replace("{{ UPDATED_DATE }}", updated_date) \
                          .replace("{{ LINKS_CHECKED_DATE }}", links_checked_date) \
                          .replace("{{ MAINTENANCE_NOTE }}", escape(p_info.get("maintenance_note", "정기 관리"))) \
                          .replace("{{ CAT_NAV_LINKS }}", nav_items_list) \
                          .replace("{{ CATEGORY_NAV_LINKS }}", category_nav_list) \
                          .replace("{{ TOC_ITEMS }}", toc_items) \
                          .replace("{{ AD_TOP }}", render_ad(AD_SLOT_TOP, ad_format="horizontal", full_width_responsive=True)) \
                          .replace("{{ AD_SIDE }}", render_ad(AD_SLOT_SIDE)) \
                          .replace("{{ INTRO_GUIDE_HTML }}", intro_guide_html) \
                          .replace("{{ CROSS_PROMO_HTML }}", "") \
                          .replace("{{ ENTRIES_HTML }}", "".join(entries)) \
                          .replace("{{ SEO_SHIELD_HTML }}", "")

    output_path = content_output_path(item)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered_cat, encoding="utf-8")
    print(f"[OK] {output_path.relative_to(OUT_DIR)} 생성 완료")

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
    """콘텐츠가 있는 모든 게시글 카테고리에 허브 아이템을 만든다."""
    posts = [it for it in items if it["type"] == "post"]
    categories = sorted({
        str(post.get("meta", {}).get("category", "")).strip()
        for post in posts
        if str(post.get("meta", {}).get("category", "")).strip()
    }, key=str.casefold)
    configured = dict(HUB_CATEGORIES)
    used_slugs = {str(item.get("slug", "")).lower() for item in items}
    for category_label in categories:
        category = category_label.upper()
        if category in configured:
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", category_label.lower()).strip("-") or "notes"
        while slug in used_slugs:
            slug = f"notes-{slug}"
        used_slugs.add(slug)
        display_name = CATEGORY_LABELS.get(category, category_label)
        configured[category] = {
            "slug": slug,
            "title": f"{display_name} 노트: {SITE_NAME} 기술 기록 모음",
            "nav_title": f"{display_name} 노트",
            "description": f"{SITE_NAME}에 기록한 {display_name} 관련 기술 메모와 참고 자료를 한곳에서 확인할 수 있습니다.",
        }

    hubs = []
    for category, info in configured.items():
        members = [p for p in posts if str(p.get("meta", {}).get("category", "")).upper() == category]
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
    for old_slug, new_slug in CATEGORY_REDIRECTS.items():
        target_url = archive_path(CATEGORY_URL_PREFIX, new_slug)
        target_label = CATEGORY_LABELS.get(new_slug.upper(), new_slug)
        output_path = OUT_DIR / CATEGORY_URL_PREFIX.strip("/") / old_slug / "index.html"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="robots" content="noindex, follow">
  <link rel="canonical" href={quoteattr(SITE_ORIGIN + target_url)}>
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


def _archive_card(item):
    href = tag_path(item["slug"]) if item["type"] == "tag" else content_path(item)
    return f"""
      <a class="home-article-card" href="{href}">
        <span class="home-article-date">{escape(item.get("published_date", ""))}</span>
        <strong>{escape(item["title"])}</strong>
        <span class="home-article-description">{escape(item["description"])}</span>
      </a>"""


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
        og_image=f"{SITE_ORIGIN}{BASE_URL}/assets/og-home.svg",
        robots=robots,
    )
    nav_html = render_nav(tpl_nav, "", top_nav_links)
    rendered = tpl_archive.replace("{{ HEAD_HTML }}", head_html) \
                          .replace("{{ NAV_HTML }}", nav_html) \
                          .replace("{{ FOOTER_HTML }}", footer_html) \
                          .replace("{{ TITLE }}", escape(title)) \
                          .replace("{{ DESCRIPTION }}", escape(description)) \
                          .replace("{{ ITEMS }}", "".join(_archive_card(item) for item in items)) \
                          .replace("{{ PAGINATION }}", pagination)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")


def build_post_archives(posts, tpl_archive, tpl_head, tpl_nav, footer_html, docs_assets, site_domain, top_nav_links):
    ordered_posts = sorted(
        posts,
        key=lambda item: (item["published_date"], item["slug"]),
        reverse=True,
    )
    page_count = max(1, (len(ordered_posts) + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE)
    archive_paths = []
    for page_number in range(1, page_count + 1):
        slug = "" if page_number == 1 else str(page_number)
        route = archive_path(POSTS_URL_PREFIX, slug)
        if page_number == 1:
            archive_paths.append(route)
        page_items = ordered_posts[
            (page_number - 1) * POSTS_PER_PAGE:page_number * POSTS_PER_PAGE
        ]
        pagination_links = []
        if page_number > 1:
            previous_slug = "" if page_number == 2 else str(page_number - 1)
            pagination_links.append(
                f'<a href="{archive_path(POSTS_URL_PREFIX, previous_slug)}">← 이전</a>'
            )
        if page_number < page_count:
            pagination_links.append(
                f'<a href="{archive_path(POSTS_URL_PREFIX, str(page_number + 1))}">다음 →</a>'
            )
        output_path = OUT_DIR / POSTS_URL_PREFIX.strip("/")
        if slug:
            output_path /= slug
        output_path /= "index.html"
        build_archive_page(
            tpl_archive, tpl_head, tpl_nav, footer_html, docs_assets,
            site_domain, top_nav_links,
            "글 목록" if page_number == 1 else f"글 목록 {page_number}페이지",
            SITE_DESCRIPTION,
            route,
            page_items,
            output_path,
            "".join(pagination_links),
            robots="index, follow" if page_number == 1 else "noindex, follow",
        )
    return archive_paths


def build_category_index(hubs, tpl_archive, tpl_head, tpl_nav, footer_html, docs_assets, site_domain, top_nav_links):
    route = archive_path(CATEGORY_URL_PREFIX)
    output_path = OUT_DIR / CATEGORY_URL_PREFIX.strip("/") / "index.html"
    build_archive_page(
        tpl_archive, tpl_head, tpl_nav, footer_html, docs_assets,
        site_domain, top_nav_links,
        "카테고리",
        f"{SITE_NAME}의 기술 기록을 주제별 카테고리로 모았습니다.",
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

    tag_index_path = archive_path(TAG_URL_PREFIX)
    build_archive_page(
        tpl_archive, tpl_head, tpl_nav, footer_html, docs_assets,
        site_domain, top_nav_links,
        "태그 목록",
        "태그별로 관련 글을 찾아볼 수 있습니다.",
        tag_index_path,
        index_items,
        OUT_DIR / TAG_URL_PREFIX.strip("/") / "index.html",
        robots="noindex, follow",
    )
    return len(grouped_tags)


def display_category_label(category):
    category_name = str(category or "NOTE")
    return CATEGORY_LABELS.get(category_name.upper(), category_name)


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
    ad_html = render_ad(AD_SLOT_MID, ad_format="auto", full_width_responsive=True)
    if not ad_html:
        return ""
    return f'<div class="post-inline-ad" aria-label="광고"><span>광고</span>{ad_html}</div>'


def insert_inline_ad(html, min_sections=3):
    """글자 수에 비례해 본문 광고 개수를 정하고, 본문 길이를 고르게 나누는 h2 앞에 배치한다."""
    marks = [m.start() for m in re.finditer(r"<h2[ >]", html)][1:]
    text_len = len(re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", html)))
    count = min(INLINE_AD_MAX, text_len // INLINE_AD_CHARS, len(marks))
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
    note = AUTHOR_NOTES.get(str(category or "").upper(), AUTHOR_NOTE_DEFAULT)
    return f"""
    <aside class="author-box" aria-label="글쓴이 소개">
      <div class="author-box-copy">
        <span class="author-box-name">{escape(AUTHOR_NAME)}</span>
        <p>{escape(AUTHOR_BIO)}</p>
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

    generate_page_og_image(docs_assets, og_filename, item["badge"], title, site_domain)
    head_html = render_head(
        tpl_head,
        title=title,
        description=description,
        tags=item.get("tags", []),
        canonical_path=content_path(item),
        og_image=f"{SITE_ORIGIN}{BASE_URL}/assets/{og_filename}",
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
        {render_ad(AD_SLOT_TOP, ad_format="horizontal", full_width_responsive=True)}
      </div>
    </div>
    """
    side_ad_block = f'<div class="sidebar-ad-box">{render_ad(AD_SLOT_SIDE)}</div>'
    if item["type"] == "post":
        content_html = insert_inline_ad(content_html)
        content_html += render_ad_block()
        content_html += render_author_box(meta.get("category"))
        content_html += render_related_posts(posts, hubs, meta.get("category"), exclude_slug=slug)
        byline = f'<span class="post-byline">글 {escape(AUTHOR_NAME)}</span>'
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
          <span>작성: {escape(AUTHOR_NAME)}</span>
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
            "author": {"@type": "Person", "name": AUTHOR_NAME},
            "mainEntityOfPage": f"{SITE_ORIGIN}{content_path(item)}",
        }
        json_ld = '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>"
    elif item["type"] == "page":
        top_ad_block = ""
        side_ad_block = ""
    rendered = tpl_post.replace("{{ JSON_LD }}", json_ld) \
                       .replace("{{ BYLINE }}", byline) \
                       .replace("{{ HEAD_HTML }}", head_html) \
                       .replace("{{ NAV_HTML }}", nav_html) \
                       .replace("{{ FOOTER_HTML }}", footer_html) \
                       .replace("{{ TOP_AD_BLOCK }}", top_ad_block) \
                       .replace("{{ SIDE_AD_BLOCK }}", side_ad_block) \
                       .replace("{{ CAT_NAV_LINKS }}", catalog_nav_list) \
                       .replace("{{ TOC_ITEMS }}", toc_items) \
                       .replace("{{ BADGE }}", escape(item["badge"])) \
                       .replace("{{ DATE }}", escape(item["updated_date"])) \
                       .replace("{{ TITLE }}", escape(title)) \
                       .replace("{{ DESCRIPTION }}", escape(description)) \
                       .replace("{{ POST_META }}", post_meta) \
                       .replace("{{ CONTENT_HTML }}", content_html) \
                       .replace("{{ CATEGORY_NAV_LINKS }}", category_nav_list) \
                       .replace("{{ AD_SIDE }}", "")

    output_path = content_output_path(item)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    print(f"[OK] {output_path.relative_to(OUT_DIR)} 생성 완료")

def main():
    if not DATA_DIR.exists():
        print(f"안내: {DATA_DIR} 디렉토리가 없어 JSON 카탈로그 없이 빌드합니다.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    clean_generated_pages()
    docs_assets = OUT_DIR / "assets"
    if (BASE_DIR / "assets").exists():
        if docs_assets.exists():
            shutil.rmtree(docs_assets)
        shutil.copytree(BASE_DIR / "assets", docs_assets)

    sync_static_files()
    site_domain = generate_github_pages_meta()

    tpl_home = read_template("template_index.html")
    tpl_cat = read_template("template_catalog.html")
    tpl_post = read_template("template_post.html")
    tpl_archive = read_template("template_archive.html")
    tpl_head = read_template("partial_head.html").replace(
        "{{ GOOGLE_TAG }}", read_template("partial_googletag.html")
    )
    tpl_nav = read_template("partial_nav.html")
    tpl_footer = read_template("partial_footer.html")

    pages_dir = BASE_DIR / "content" / "pages"
    items = load_all_contents(DATA_DIR, POSTS_DIR, pages_dir)
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
    build_tools_page(nav_html, footer_html)

    all_posts = [it for it in items if it["type"] == "post"]
    category_nav_items = [f'<li><a href="{site_root_path()}">🏠 전체 노트</a></li>']
    for hub in hubs:
        count = len([
            p for p in all_posts
            if str(p.get("meta", {}).get("category", "")).upper() == hub["category"]
        ])
        category_nav_items.append(
            f'<li><a href="{content_path(hub)}">{escape(hub["nav_title"])}'
            f' <span class="sidebar-count">{count}</span></a></li>'
        )
    category_nav_list = "".join(category_nav_items)

    archive_paths = [build_category_index(
        hubs, tpl_archive, tpl_head, tpl_nav, footer_html, docs_assets,
        site_domain, top_nav_links,
    )]
    archive_paths.extend((
        archive_path("tools"),
        archive_path("tools/regex-live-tester"),
    ))
    archive_paths.extend(build_post_archives(
        all_posts, tpl_archive, tpl_head, tpl_nav, footer_html, docs_assets,
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
    generate_sitemap(items + hubs, archive_paths)
    generate_rss(all_posts)
    generate_robots()

    print(
        f"\n[DONE] [{site_domain}] 사이트 빌드 완료! "
        f"(총 {len(items)}개 콘텐츠, 태그 아카이브 {tag_count}개)"
    )

if __name__ == "__main__":
    main()