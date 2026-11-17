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
카탈로그의 `sites`는 목록 파일의 항목입니다. 일부 내부 HTML
조각은 현재 Python에서 생성하므로 Jinja2만으로 모든 내부 구조를 바꾸지는 못합니다.

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

## 안전과 호환성

텍스트와 HTML 속성은 기본적으로 자동 이스케이프됩니다. `HEAD_HTML`,
`CONTENT_HTML`, `INTRO_GUIDE_HTML` 등 Naru가 만든 HTML 조각은 그대로 삽입됩니다.
Markdown에 직접 쓴 HTML은 정화하지 않으므로 신뢰할 수 있는 콘텐츠만 빌드하세요.
외부 데이터에 `|safe`를 적용하면 이스케이프를 우회하므로 주의하세요.

정의되지 않은 변수는 오류입니다. 선택적 값에는 `default` 필터나 `is defined`
조건을 사용하세요. 최상위 및 정적으로 참조된 템플릿 문법은 출력 정리 전에
검사합니다. 동적 include나 렌더링 중의 미정의 변수 오류는 빌드 도중에 발생할 수
있지만 임시 출력에서 빌드하므로 기존 출력은 유지됩니다.

기존 대문자 자리 표시자는 해당 템플릿에서 계속 사용할 수 있지만, 다른 템플릿의
변수를 사용하거나 오타가 있으면 미정의 변수 오류가 발생합니다. 기존에 문자 그대로
출력되던 Jinja 문법을 표시하려면 `{% raw %}` 블록을 사용하세요. `static/`은
템플릿으로 렌더링하지 않으며 `static/tools/index.html`의 기존 공통 내비게이션과
푸터 자리 표시자만 별도로 치환합니다.