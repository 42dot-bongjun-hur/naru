# 템플릿 가이드

Naru는 Jinja2로 HTML 템플릿을 렌더링합니다. 사이트의 `templates/`에 파일을
두면 같은 이름의 패키지 기본 템플릿보다 우선합니다. 없는 파일은 기본 템플릿을
사용하며 `{% include %}`와 `{% extends %}`도 같은 순서로 파일을 찾습니다.
템플릿은 프로젝트 작성자가 관리하는 신뢰할 수 있는 코드로 취급합니다.

## 작성 예제

`templates/template_catalog.html`에서 사이트 목록을 직접 구성할 수 있습니다.

```jinja
<!doctype html>
<html lang="ko">
<head>{{ HEAD_HTML }}</head>
<body>
  {{ NAV_HTML }}
  <h1>{{ TITLE }}</h1>
  {{ INTRO_GUIDE_HTML }}
  <ul>
    {% for entry in sites %}
      <li><a href="{{ entry.url }}">{{ entry.name }}</a></li>
    {% endfor %}
  </ul>
  {{ FOOTER_HTML }}
</body>
</html>
```

기본 카탈로그의 표 행은 `partial_catalog_entries.html`에서 정의합니다. 해당
파일만 사이트에서 덮어쓰거나 카탈로그 템플릿에서 직접 반복할 수 있습니다.

## 공통 변수

- `site`: 검증된 사이트 설정. 예를 들어 `site.site_name`, `site.base_url`.
- 설정의 대문자 변수: `SITE_NAME`, `SITE_ORIGIN`, `BASE_URL` 등 기존 변수.
- `content_url(item)`, `tag_url(slug)`, `archive_url(prefix, slug='')`,
  `site_root_url()`: 설정된 URL 접두사를 반영하는 경로 함수.
- 각 페이지 템플릿의 `HEAD_HTML`, `NAV_HTML`, `FOOTER_HTML`: 공통 HTML 조각.

## 페이지별 변수

| 템플릿 | 주요 변수 |
| --- | --- |
| `template_index.html` | `items`, `home_groups`, `recent_entries`, `infeed_ad`, `SLOGAN_EN_PLAIN`, `SLOGAN_EN`, `SLOGAN_KO`, `RECENT_POSTS`, `HOME_CONTENT_SECTIONS`, `QUICK_MENU`, `TOPIC_LINKS` |
| `template_post.html` | `page`, `TITLE`, `DESCRIPTION`, `DATE`, `BADGE`, `CONTENT_HTML`, `POST_META`, `JSON_LD`, `BYLINE`, `TOC_ITEMS`, `CAT_NAV_LINKS`, `CATEGORY_NAV_LINKS`, `TOP_AD_BLOCK`, `SIDE_AD_BLOCK`, `AD_SIDE` |
| `template_catalog.html` | `page`, `sites`, `TITLE`, `DESCRIPTION`, `PUBLISHED_DATE`, `UPDATED_DATE`, `LINKS_CHECKED_DATE`, `MAINTENANCE_NOTE`, `INTRO_GUIDE_HTML`, `ENTRIES_HTML`, `TOC_ITEMS`, `CAT_NAV_LINKS`, `CATEGORY_NAV_LINKS`, `AD_TOP`, `AD_SIDE`, `AD_IN_TABLE`, `CROSS_PROMO_HTML`, `SEO_SHIELD_HTML` |
| `template_archive.html` | `items`, `archive_entries`, `TITLE`, `DESCRIPTION`, `ITEMS`, `PAGINATION` |

`page`와 `items`는 콘텐츠 정보이며 `page.title`, `page.slug`, `page.meta` 등을
사용할 수 있습니다. `home_groups`는 그룹과 카테고리별 글을, `recent_entries`는
최근 글과 카테고리 이름을, `archive_entries`는 목록 항목과 URL을 담습니다.
기본 화면은 `partial_home_groups.html`, `partial_home_recent.html`,
`partial_archive_items.html`을 사용하며 같은 이름의 파일로 덮어쓸 수 있습니다.
카탈로그의 `sites`는 목록 파일의 항목입니다. 글의 부가 정보와 공통 링크,
광고, OG 이미지도 아래의 부분 템플릿에서 정의합니다.

공통 부분 템플릿에서는 사이트 설정 외에 다음 변수를 사용할 수 있습니다.

- `partial_head.html`: `TITLE`, `DESCRIPTION`, `KEYWORDS`, `CANONICAL_PATH`,
  `OG_IMAGE`, `OG_TYPE`, `ROBOTS`, `CSS_VERSION`, `THEME_STYLESHEETS`, `GOOGLE_TAG`.
- `partial_googletag.html`: `partial_head.html`과 같은 페이지 정보 및 사이트 설정.
- `partial_nav.html`: `TOP_NAV_LINKS`, `NAV_RIGHT`.
- `partial_footer.html`: `SITE_DOMAIN`, `FOOTER_GROUP_LINKS`, `FOOTER_INFO_LINKS`, `pages`.
- `partial_catalog_entries.html`: `sites`, `page`, `AD_IN_TABLE`과 카탈로그 변수.

`THEME_STYLESHEETS`는 테마 토큰 CSS와 설정된 사용자 CSS의 URL 목록입니다.
기본 head는 기본 CSS 다음에 이 목록을 순서대로 불러옵니다. head를 직접
작성했다면 같은 반복문을 추가하세요. [테마 가이드](themes.md)에 적용 예제와
기존 CSS와의 우선순위를 설명합니다. 검증된 테마 설정은 `site.theme`으로
접근할 수 있습니다.

## 엔진 부분 템플릿

Python 엔진은 콘텐츠 선택·URL·읽기 시간·광고 위치 같은 데이터를 계산하고,
화면 마크업은 부분 템플릿에서 렌더링합니다. 다음 파일을 사이트의 `templates/`에
두면 해당 부분만 변경할 수 있습니다. 모든 파일에서 `site`와 공통 설정 변수에
접근할 수 있으며, 표의 변수는 각 렌더링 호출에 추가로 전달됩니다.

| 파일 | 추가 변수 |
| --- | --- |
| `partial_post_meta.html` | `page`, `category_label`, `reading_minutes` |
| `partial_post_byline.html` | 공통 작성자 설정 |
| `partial_author_box.html` | 카테고리별 작성자 메모인 `note` |
| `partial_related_posts.html` | `related_entries` (`item`, `category_label`), `hub`, `heading` |
| `partial_toc.html` | 평탄화한 `headings` (`id`, `name`) |
| `partial_nav_links.html` | `links`, `<li>` 사용 여부인 `list_items` |
| `partial_nav_status.html` | `latest_date` |
| `partial_group_icon.svg` | `icon_name` |
| `partial_hub_posts.html` | 카테고리 콘텐츠 목록인 `members` |
| `partial_catalog_intro.html` | 렌더링된 Markdown인 `intro_html` |
| `partial_ad.html` | `slot_id`, `ad_format`, `infeed`, `layout_key`; 일반 광고의 `full_width_responsive` |
| `partial_ad_block.html` | `placement` (`top`, `side`, `inline`), 렌더링된 `ad_html` |
| `partial_json_ld.html` | 구조화된 `schema`; 기본 템플릿은 `tojson` 필터 사용 |
| `partial_slogan.html` | 일반 텍스트와 강조 문구가 교대로 담긴 `parts` |
| `template_redirect.html` | `target_url`, `target_label` |
| `image_og.svg` | `code_label`, `title_line1`, `title_line2`, `site_domain` |

`links` 항목에는 `href`, `label`이 있으며 용도에 따라 `class_name`, `icon`,
`date`, `count`가 추가됩니다. `icon`은 렌더링된 SVG이고 다른 값은 일반 데이터입니다.
`hub`는 없으면 `None`입니다. 선택적 필드는 `.get()`이나 `default`로 처리하세요.

예를 들어 작성자 표시만 변경하려면 `templates/partial_post_byline.html`에
다음을 작성합니다.

```jinja
<small class="post-byline">{{ AUTHOR_NAME }}의 기록</small>
```

기존 `POST_META`, `BYLINE`, `TOC_ITEMS`, `CONTENT_HTML`, `CAT_NAV_LINKS`,
`CATEGORY_NAV_LINKS`, `PAGINATION` 등 대문자 변수는 유지됩니다. 기존 사이트의
전체 페이지 템플릿을 수정하지 않아도 내부 조각은 새 부분 템플릿을 사용합니다.
Markdown 자체의 변환은 Markdown 확장이 담당하며, RSS·sitemap은 화면 템플릿이
아니라 표준 XML API로 직렬화합니다.

## 안전과 호환성

텍스트와 HTML 속성은 기본적으로 자동 이스케이프됩니다. `HEAD_HTML`,
`CONTENT_HTML`, `INTRO_GUIDE_HTML` 등 Naru가 만든 HTML 조각은 그대로 삽입됩니다.
Markdown에 직접 쓴 HTML은 정화하지 않으므로 신뢰할 수 있는 콘텐츠만 빌드하세요.
외부 데이터에 `|safe`를 적용하면 이스케이프를 우회하므로 주의하세요.

정의되지 않은 변수는 오류입니다. 선택적 값에는 `default` 필터나 `is defined`
조건을 사용하세요. 최상위 및 정적으로 참조된 템플릿 문법은 출력 정리 전에
검사하며 엔진이 사용하는 기본 HTML·SVG 템플릿도 검사 대상입니다.
동적 include나 렌더링 중의 미정의 변수 오류는 빌드 도중에 발생할 수
있지만 임시 출력에서 빌드하므로 기존 출력은 유지됩니다.

기존 대문자 자리 표시자는 해당 템플릿에서 계속 사용할 수 있지만, 다른 템플릿의
변수를 사용하거나 오타가 있으면 미정의 변수 오류가 발생합니다. 기존에 문자 그대로
출력되던 Jinja 문법을 표시하려면 `{% raw %}` 블록을 사용하세요. `static/`은
템플릿으로 렌더링하지 않으며 `static/tools/index.html`의 기존 공통 내비게이션과
푸터 자리 표시자만 별도로 치환합니다.