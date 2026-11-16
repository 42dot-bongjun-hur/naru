# Architecture

## 책임 경계

Naru는 사이트 콘텐츠를 소유하지 않는 재사용 가능한 엔진으로 설계합니다.

```text
site project A ─┐
                ├── shared Naru package ──> each site's own output directory
site project B ─┘
```

각 사이트 프로젝트가 소유할 항목:

- 사이트 이름, 원본 URL, 기본 경로, 분류명 등 사이트 설정
- Markdown 글과 정형 데이터
- 콘텐츠와 독립적으로 덮어쓸 템플릿, 스타일, 이미지와 기타 정적 파일
- 빌드 결과물 및 배포 설정

Naru가 소유할 항목:

- 설정 파싱과 검증
- 콘텐츠 로딩 및 front matter 정규화
- URL/출력 경로 계산
- HTML 렌더링과 정적 리소스 복사
- 기본 템플릿과 스타일 제공
- RSS, sitemap, robots.txt 등 선택적 산출물 생성

각 사이트는 Naru 패키지를 설치해 사용하고 자체 출력 디렉터리를 관리합니다.
Naru는 다른 사이트의 출력이나 입력 디렉터리를 빌드 결과로 사용하지 않도록
출력 경로와 소유권을 확인합니다.

## 패키지 경계

- `naru.cli`: 명령행 인자, 출력 경로 검증과 빌드 프로세스 실행
- `naru.config`: 사이트 설정 로딩 및 검증
- `naru.engine.loader`, `metadata`: 콘텐츠 로딩과 front matter 정규화
- `naru.engine.build`, `routes`: 페이지 렌더링과 URL·출력 경로 계산
- `naru.engine.seo`: RSS, sitemap, robots.txt와 검색 엔진 메타데이터
- `naru.engine.ads`: 광고 단위 렌더링

`content/posts/`와 `content/pages/`의 Markdown 외에도
`content/data/*.json`의 카탈로그를 읽습니다. 카탈로그는 필수 메타데이터를
`page_info`에, 목록 항목을 `sites` 배열에 담으며 콘텐츠 페이지, 사이트맵과
홈의 최신 콘텐츠, `/posts/` 통합 목록, 카테고리 목록에 반영됩니다. JSON
카탈로그의 기본 카테고리는 `bookmark`이며, Markdown 글과 같은 목록 카드로
표시되고 카테고리 허브와 RSS에도 포함됩니다.
현재 배포 예제는 `bookmark` 카테고리의 Markdown 글이며, 같은 데이터를 JSON으로
표현한 대안은 `examples/basic-site/alternatives/python-ssg.json`에 있습니다.

현재 엔진은 모듈 전역 설정을 사용합니다. CLI는 빌드마다 별도 Python
프로세스를 실행해 사이트 설정이 섞이지 않도록 합니다.

## 설정과 출력

`naru build`는 사이트 루트와 출력 디렉터리를 받습니다. 사이트 루트의
`naru.yml`에서 설정을 로드하고 검증합니다. 출력 폴더는 비어 있거나 동일한
사이트의 Naru 빌드가 남긴 `.naru-output` 표식이 있어야 합니다.

빌드 시 출력 폴더의 HTML과 일부 정적 파일을 정리하거나 교체합니다. 따라서
사용자가 관리하는 파일은 출력 폴더가 아닌 콘텐츠·정적 파일 디렉터리에 둡니다.
설정은 `site_name`과 `site_origin`만 필수이며 나머지는 검증된 기본값을
사용합니다. 사이트 템플릿이 있으면 파일별로 우선하고, 없는 템플릿은
패키지에 포함된 기본 파일을 사용합니다. 기본 헤더를 사용하는 사이트는
패키지 스타일을 사용하거나 사이트의 `assets/naru.css`로 덮어쓸 수 있습니다.
현재 렌더링은 정해진 템플릿 자리 표시자와 페이지 구조를 사용합니다.

## 초기 설정 스케치

`examples/basic-site/naru.yml`은 전체 설정 필드의 예시입니다. 포함된 예제
글은 패키지의 기본 템플릿과 스타일로 빌드할 수 있습니다.

## 호환성 원칙

- 잘못된 설정이나 누락된 파일은 원인을 포함해 실패시킵니다.
- 사이트별 URL 경로와 출력 루트를 빌드마다 명시적으로 지정합니다.
- 생성 파일과 사용자가 관리하는 정적 파일의 소유권을 구분합니다.
- 설정과 콘텐츠의 변경이 다른 사이트의 빌드에 영향을 주지 않도록 합니다.
