# Casper-inspired Naru Journal

[Ghost의 Casper](https://github.com/TryGhost/Casper)를 시각적 참고로 삼아
Naru용으로 새로 작성한 예제입니다. 큰 마스트헤드, 이미지 중심 글 목록,
절제된 메타데이터와 읽기 본문을 보여줍니다. 공식 Casper의 소스 코드를
복사하거나 Ghost Handlebars 템플릿을 이식한 테마는 아닙니다.

## 실행

저장소 루트에서 개발 버전 Naru를 설치한 뒤 실행합니다.

```powershell
python -m naru serve --site-root examples/casper-site --site-origin https://example.com
```

기본 미리보기 주소는 `http://127.0.0.1:8000/`입니다. 배포용 빌드는
`serve` 대신 `build --output _site`를 사용하고 `site_origin`에는 실제
게시할 도메인을 지정하세요. 테마 설정은 Naru 0.2.1부터 사용할 수 있습니다.

## 구성

- `naru.yml`: 기본 테마의 색상·본문 폭과 사용자 CSS를 설정합니다.
- `templates/template_index.html`: 최근 글을 이미지 피드로 표시합니다.
- `templates/template_post.html`: 대표 이미지와 읽기 본문을 표시합니다.
- `static/styles/casper.css`: 사이트 전용 스타일입니다.
- `content/posts/`: 세 편의 샘플 글입니다.
- `static/images/`: 로컬 사진과 출처입니다.

글의 `feature_image`는 `static/` 기준 이미지 경로입니다.
`feature_image_alt`에는 사진 설명을 적습니다. 두 필드는 이 예제의
템플릿에서 사용하는 선택적 메타데이터이며 Naru 공통 대표 이미지 기능은
아닙니다. 이미지가 없는 글도 표시됩니다. 홈은 `home_recent_posts`개까지
표시하고 나머지는 모든 글 목록에서 볼 수 있습니다.

다른 프로젝트에 적용하려면 두 템플릿과 CSS를 복사하고 `theme` 설정을
추가하세요. 글 목록·카테고리·태그 페이지에는 패키지 기본 템플릿을
사용합니다. Ghost의 검색·구독·멤버십 기능은 포함하지 않습니다.