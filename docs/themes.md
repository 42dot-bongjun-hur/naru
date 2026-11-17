# 테마 가이드

템플릿이나 CSS를 복사하지 않고 `naru.yml`의 `theme` 설정으로 기본 화면을
꾸밀 수 있습니다. 설정을 생략하면 기존 기본 테마인 `default`를 사용합니다.
이 기능은 개발 중인 저장소 기준이며 PyPI 0.2.0에는 포함되지 않습니다.

## 빠른 적용

기존 사이트 설정에 다음 블록을 추가하세요.

```yaml
theme:
  preset: docs
  accent_color: "#087f78"
  accent_hover: "#065f59"
  font_family: '"Segoe UI", "Malgun Gothic", sans-serif'
  content_width: 60rem
```

`default`는 기존 파란색 링크와 56rem 본문 폭을 유지합니다. `docs`는 밝은
중성 배경과 청록색 링크, 64rem 본문 폭을 제공합니다. 두 프리셋은 같은
HTML 구조와 토큰을 사용하며, 명시한 값이 프리셋보다 우선합니다.
본문 폭은 최댓값이며 모바일에서는 화면에 맞춰 줄어듭니다.

사이트별 템플릿과 사용자 CSS를 조합하는 더 큰 예제는
[Casper 스타일 저널](../examples/casper-site/README.md)을 참고하세요.
Ghost의 Casper를 시각적으로 참고해 새로 작성한 Naru 예제이며, 공식 Ghost
테마를 그대로 불러오는 기능은 아닙니다. 기본형·문서형 프리셋은 유지됩니다.

## 디자인 토큰

모든 토큰은 선택 사항입니다. 색상은 `#RGB` 또는 `#RRGGBB` 형식을 사용합니다.
글꼴은 CSS 글꼴 목록으로 지정하며 자동으로 다운로드하지 않습니다. 웹폰트를
사용하려면 사용자 CSS에 `@font-face`와 폰트 파일 경로를 정의하세요.

| 설정 | 역할 | 기본값 (`default`) |
| --- | --- | --- |
| `accent_color` | 링크, 강조, 키보드 포커스 | `#2459a6` |
| `accent_hover` | 링크를 가리킬 때의 색 | `#173d78` |
| `background` | 페이지 배경 | `#f5f7fa` |
| `surface` | 본문과 항목 배경 | `#ffffff` |
| `text_color` | 본문 글자 | `#202b3a` |
| `muted_color` | 설명, 날짜, 푸터 | `#647084` |
| `border_color` | 구분선, 표와 항목 테두리 | `#dce2ea` |
| `code_background` | 코드와 보조 요소 배경 | `#edf1f6` |
| `font_family` | 본문 글꼴 | 시스템 글꼴 목록 |
| `mono_font_family` | 코드 글꼴 | `ui-monospace, "Cascadia Code", Consolas, monospace` |
| `content_width` | 본문 최대 폭 | `56rem` |

본문 폭에는 양수와 `rem`, `px`, `ch` 단위를 사용합니다. 알 수 없는 프리셋과
토큰, 잘못된 CSS 값은 설정 오류입니다. 색 조합을 바꿀 때는 본문·링크·배경의
명도 대비도 함께 확인하세요. 강조색과 hover 색은 별도 토큰입니다.

## 사용자 CSS

더 세부적인 조정은 `static/styles/site.css`처럼 사이트 안에 CSS 파일을 두고
등록합니다. 목록 순서대로 적용되며 원래 경로에서 제공하므로 CSS 내부의
상대 이미지·폰트 경로도 유지됩니다.

```yaml
theme:
  preset: docs
  custom_css:
    - styles/site.css
```

```css
/* static/styles/site.css */
.site-name {
  color: var(--naru-accent-color);
}

article h2 {
  padding-bottom: 0.4rem;
  border-bottom: 1px solid var(--naru-border-color);
}
```

경로는 `static/` 기준 상대 경로이며 실제 CSS 파일이 있어야 합니다.
외부 URL, 절대 경로, `..`를 통한 상위 폴더 접근은 허용하지 않습니다.
각 토큰의 CSS 변수는 밑줄을 하이픈으로 바꾸고 `--naru-`를 붙인 이름입니다.
예를 들어 `content_width`는 `--naru-content-width`입니다.

적용 순서는 기본 CSS → 프리셋과 토큰 → 사용자 CSS입니다. 생성된
`assets/naru-theme.css`는 Naru 전용 파일이므로 사이트에서 같은 경로의 파일을
제공하면 빌드 오류입니다. 스타일시트 URL에는 내용 기반 버전이 붙어 변경 후
오래된 브라우저 캐시가 계속 사용되지 않도록 합니다.

## 기존 프로젝트 호환성

기존 `assets/naru.css` 또는 `static/assets/naru.css`는 계속 기본 CSS보다
우선합니다. 사용자 CSS의 고정 색상·폭은 토큰으로 자동 변환되지 않으므로,
설정으로 제어할 속성에 `var(--naru-...)`를 사용하거나 전체 교체 대신
`theme.custom_css`로 옮기세요. 설정 파일만 추가해 사용자 CSS 전체를
자동으로 재디자인하지는 않습니다.

직접 작성한 `templates/partial_head.html`도 그대로 유지합니다. 이 경우
기존 기본 CSS 링크 다음에 아래 코드를 추가해야 테마와 사용자 CSS가 적용됩니다.

```jinja
{% for stylesheet in THEME_STYLESHEETS %}
<link rel="stylesheet" href="{{ stylesheet }}">
{% endfor %}
```

사이트 설정과 CSS를 변경한 뒤 `naru check`로 검사하거나 `naru serve`로
미리보기할 수 있습니다. 생성된 출력 CSS를 직접 수정하지 말고 설정과
`static/`의 원본을 변경하세요. 테마 설정을 제거하고 다시 빌드하면 기본
토큰으로 돌아갑니다.