# 카탈로그 가이드

카탈로그는 글의 소개와 구조화된 사이트 목록을 한 페이지에 표시합니다.
`content/posts/`에 Markdown 파일과 같은 이름의 `.sites.yml` 파일을 둡니다.
하위 폴더에서도 같은 방식으로 사용할 수 있습니다.

```text
content/posts/
└── bookmark/
   ├── python-ssg.md
   └── python-ssg.sites.yml
```

Markdown에는 일반 글과 같은 필수 front matter를 작성하고 `layout: catalog`를
추가합니다. 본문은 사이트 목록 앞의 소개로 표시합니다. `category`를 생략하면
첫 번째 폴더명을 사용하고, 루트에 있는 카탈로그는 `bookmark`를 사용합니다.
`links_checked_date`와 `maintenance_note`는 선택 항목입니다.
파일 이름과 사이트 목록의 이름이 일치해야 하며 `slug`는 별도로 지정한 페이지 주소입니다.

`.sites.yml`에는 목록을 YAML 배열로 작성합니다.

```yaml
- id: pelican
  name: Pelican
  url: https://getpelican.com/
  description: Python 정적 사이트 생성기
- id: mkdocs
  name: MkDocs
  url: https://www.mkdocs.org/
  description: 프로젝트 문서 생성기
  status: active
```

목록 순서대로 표시합니다. `id`, `name`, `url`, `description`은 필수이며
`id`는 중복 없는 영문 소문자 kebab-case, URL은 HTTP(S) 주소여야 합니다.
`status`는 `active`, `inactive`, `error`, `unknown` 중 하나이며 생략하면
`unknown`입니다. 상태는 작성자가 관리하는 값으로, Naru는 접속 여부를 자동으로
확인하지 않습니다. 빈 목록은 `[]`로 작성할 수 있습니다. 잘못된 값이나 알 수 없는
필드, 누락된 목록 파일은 빌드 오류입니다.

## 이전 형식에서 옮기기

이 저장소의 개발 버전에서는 이전 JSON 카탈로그와 Markdown front matter의 `sites`를
지원하지 않습니다. 기존 출력이 조용히 사라지지 않도록 빌드에서 오류로 알립니다.

1. 기존 Markdown의 front matter에서 `sites` 배열을 빼내 동명의 `.sites.yml`에
   최상위 YAML 배열로 저장합니다.
2. JSON 카탈로그는 `page_info`의 메타데이터를 Markdown front matter에 옮기고
   `layout: catalog`를 추가합니다. `intro_guide` 내용은 Markdown 본문으로 옮깁니다.
3. JSON의 `sites` 배열을 동명의 `.sites.yml`에 YAML 배열로 옮깁니다. 각 항목의
   `id`, `name`, `url`, `description`을 확인하고 `display_order` 등 지원하지 않는
   필드를 제거합니다. 순서는 배열 순서로 정합니다.
4. 이전 JSON 파일을 `content/data/`에서 제거하고 새 빌드의 페이지와 주소를 확인합니다.

자세한 예제는 [Markdown 소개](../examples/basic-site/content/posts/bookmark/python-ssg.md)와
[사이트 목록](../examples/basic-site/content/posts/bookmark/python-ssg.sites.yml)을 참고하세요.