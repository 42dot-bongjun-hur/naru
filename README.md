# Naru

**콘텐츠는 각자, 생성기는 함께.**

Naru는 여러 사이트가 하나의 정적 사이트 생성 엔진을 공유하면서도 설정,
콘텐츠, 테마와 빌드 결과물은 각 프로젝트 안에서 독립적으로 관리하기 위한
Python 기반 생성기 프로젝트입니다.

> 0.1 시험판: 기본 템플릿과 최소 설정을 제공하며, 정해진 페이지 구조를
> 사용합니다.

## 기능

- `naru.yml`을 이용한 사이트 설정과 출력 경로 분리
- 패키지에 포함된 기본 템플릿과 스타일, 사이트별 템플릿 덮어쓰기
- JSON 카탈로그를 HTML 링크·북마크 모음 페이지로 생성
- Markdown 블로그 글과 페이지 생성
- 블로그 글과 JSON 카탈로그를 홈의 최신 목록과 카테고리별 목록에 함께 표시
- 카테고리·태그 아카이브, RSS, sitemap, robots.txt 생성
- 정적 파일과 글에 첨부한 이미지 복사
- 예제 사이트의 GitHub Actions → Pages 자동 배포

## 어떤 사이트를 만들 수 있나요?

Naru는 콘텐츠를 JSON 또는 Markdown으로 작성하고, 배포할 수 있는 정적 HTML
사이트를 생성합니다.

| 용도 | 입력 | 생성 결과 |
| --- | --- | --- |
| 링크·북마크 모음 | `content/data/*.json`의 `page_info`와 `sites` | JSON 파일마다 `/슬러그/` 카탈로그 페이지 |
| 블로그 | `content/posts/*.md`의 YAML front matter와 Markdown | `/posts/슬러그/` 글 페이지 |
| 카테고리·태그 | 글 front matter의 `category`, `tags`; JSON `page_info.category` | 홈의 카테고리별 목록과 `/category/슬러그/`, `/tags/태그/` 아카이브 |
| 일반 페이지 | `content/pages/*.md` | `/슬러그/` 페이지 |

예를 들어 북마크나 참고 링크를 JSON 카탈로그로 정리하면서, 같은 사이트에
`blog` 카테고리의 Markdown 글을 함께 둘 수 있습니다. 두 콘텐츠 유형은
홈의 최신 콘텐츠 목록에 같이 나오며, JSON 카탈로그는 `bookmark`, 블로그 글은
`blog` 같은 카테고리별 목록과 아카이브에 모을 수 있습니다. JSON은 그대로
노출되지 않고 Naru가 사이트 템플릿에 맞는 HTML 페이지로 변환합니다.
생성물은 GitHub Pages 등 정적 호스팅에 배포할 수 있으며, 이 저장소의 예제는
`naru.devbj.com`으로 자동 배포하도록 구성되어 있습니다.

## 프로젝트 구조

```text
naru/
├── .github/workflows/            # CI 및 예제 사이트 배포
├── docs/                       # 설계 및 사용자 문서
├── examples/basic-site/        # 사이트 설정과 콘텐츠 예시
├── src/naru/                   # 설치 가능한 Python 패키지와 CLI
├── tests/                      # 자동화 테스트
├── pyproject.toml
└── README.md
```

## 설치

Python 3.11 이상이 필요합니다.
이전에 Git에서 0.1.1을 설치한 환경이라면 두 배포 패키지가 같은 모듈을
사용하므로 설치하기 전에 `python -m pip uninstall naru`로 제거하세요.

```powershell
python -m pip install "naru-sitegen==0.1.3"
```

> [!IMPORTANT]
> **자신의 사이트를 배포하기 전에 `naru.yml`의 `site_origin`을 반드시
> 본인이 소유하고 DNS를 관리하는 도메인으로 바꾸세요.** 예제의
> `https://naru.devbj.com`은 이 저장소의 데모 전용 도메인입니다. 그대로
> 사용하면 생성되는 `CNAME`, canonical URL, RSS 링크도 데모 도메인을
> 가리키므로 다른 사이트에 사용하면 안 됩니다.

배포 패키지 이름은 `naru-sitegen`이며 Python 모듈과 CLI 이름은 `naru`입니다.
각 사이트는 검증한 버전을 의존성 파일에 고정하고, 새 버전이 나왔을 때
사이트 빌드를 검증한 후 버전을 갱신합니다.

## PyPI 배포

최초 게시 전에 PyPI 계정에서 새 프로젝트 `naru-sitegen`의 pending trusted
publisher를 등록합니다. 소유자는 `bjnhur`, 저장소는 `naru`, 워크플로 파일은
`publish.yml`, 환경은 `pypi`입니다. GitHub 저장소에 같은 이름의 환경이
필요하며 필요한 경우 환경 보호 규칙을 설정합니다.

버전을 올릴 때는 `pyproject.toml`과 `src/naru/__init__.py`의 버전 및 CLI
테스트를 함께 갱신하고 테스트를 통과시킵니다. 변경을 기본 브랜치에 반영한
후 같은 커밋에 `v` 접두사가 붙은 버전 태그를 만들고 push합니다. 예를 들어
`0.1.2`의 태그는 `v0.1.2`입니다. 태그 push 시 워크플로가 태그와 버전 일치,
테스트 및 배포 파일을 확인한 후 PyPI에
게시합니다. 한 번 업로드한 배포 파일은 동일한 이름으로 다시 업로드할 수
없으므로, 게시 후 변경에는 새 버전이 필요합니다.

## 개발 환경

Python 3.11 이상이 필요합니다.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

CLI 기반을 확인합니다.

```powershell
naru --help
naru --version
```

사이트 프로젝트에서 빌드를 실행합니다.

```powershell
naru build --site-root . --output _site
```

사이트 루트의 `naru.yml`을 읽습니다. `--output`을 생략하면
`<site-root>/docs`를 사용합니다. 출력 폴더는 비어 있거나 같은 사이트의
Naru가 생성한 `.naru-output` 표식이 있어야 합니다. 기존 폴더를 자동으로
인수하지 않으므로 처음에는 빈 출력 경로를 지정하세요. Naru가 관리하는
출력 폴더의 HTML과 일부 정적 파일은 빌드할 때 정리·교체하므로, 직접 작성한
파일을 그곳에 두지 마세요. 설정 예시는 `examples/basic-site/naru.yml`입니다.

## 최소 사이트

0.1.3에서는 사이트 폴더의 `naru.yml`에 이름과 공개 주소만 지정해도
기본 템플릿으로 빌드할 수 있습니다.

```yaml
site_name: My Journal
site_origin: https://example.com
```

`site_origin`은 경로가 없는 HTTP(S) 주소입니다. 게시할 주소로 바꾼 뒤
사이트 폴더에서 다음을 실행합니다.

```powershell
python -m naru build --site-root . --output dist
```

## 예제 사이트 배포

`examples/basic-site`는 `https://naru.devbj.com`을 사용하며,
`.github/workflows/deploy-example.yml`이 `main` 브랜치 push 또는 수동 실행 시
Naru를 저장소 소스에서 설치해 사이트를 빌드하고 GitHub Pages에 배포합니다.
이 예제의 DNS CNAME과 저장소 **Settings → Pages**의 **GitHub Actions** 배포
소스 및 `naru.devbj.com` 사용자 지정 도메인은 설정되어 있습니다. 변경을
`main`에 push하면 `https://naru.devbj.com`에 자동 배포됩니다.
`naru.devbj.com`은 이 데모 전용이므로 다른 사이트 설정에 복사해 사용하지 마세요.

글은 `content/posts/` 아래 Markdown 파일로 추가합니다. 폴더나 글이 없어도
빈 사이트를 빌드할 수 있습니다. 템플릿, 스타일, 정적 파일은 필요할 때만
사이트에서 제공합니다.

```text
my-site/
├── naru.yml
├── requirements.txt          # 사이트의 Naru 버전 고정
├── content/
│   ├── posts/                # Markdown 글
│   ├── pages/                # Markdown 페이지 (선택)
│   └── data/                 # JSON 카탈로그 (선택)
├── templates/                # 기본 템플릿 덮어쓰기 (선택)
├── static/                   # 정적 파일 (선택)
└── assets/                   # 스타일과 이미지 (선택)
```

`content/data/*.json`에는 링크 모음처럼 구조화된 카탈로그를 둡니다.
JSON의 최상위 `page_info`에는 글과 같은 제목, 슬러그, 설명, 게시일,
수정일, 태그와 함께 `links_checked_date`, `intro_guide` 등을 지정하고,
`sites` 배열에는 각 항목의 `name`, `url`, `description`, `status`를
넣습니다. Naru는 각 파일을 카탈로그 페이지로 빌드합니다. 예제는 Python
정적 사이트·문서 생성기를 모은
[`examples/basic-site/content/data/python-ssg.json`](examples/basic-site/content/data/python-ssg.json)이며,
`python-ssg/index.html`로 출력됩니다.

카테고리, 광고, URL 경로 등을 생략하면 기본값을 사용합니다. 생략 가능한
필드라도 값을 지정했다면 유효해야 하며, 알 수 없는 필드는 오류입니다.
사용 가능한 전체 설정은 `examples/basic-site/naru.yml`을 참고하세요.
작성자 이름을 생략하면 사이트 이름을 사용합니다. 현재 일부 카테고리 설명과
화면 문구는 기존 기술 블로그와 한국어를 전제로 하므로 범용 사이트에
사용하기 전 결과물을 확인하세요.

## 템플릿과 스타일

별도 템플릿이 없으면 패키지에 포함된 기본 템플릿을 사용합니다. 사이트의
`templates/`에 같은 이름의 파일이 있으면 그 파일을 우선하고, 없는 파일은
기본 템플릿을 사용합니다. 템플릿 자리 표시자와 페이지 구조는 아직 고정되어
있으므로 다른 생성기의 테마를 그대로 사용할 수는 없습니다.

```text
templates/
├── template_index.html, template_post.html
├── template_catalog.html, template_archive.html
└── partial_head.html, partial_googletag.html, partial_nav.html, partial_footer.html
```

기본 헤더는 패키지의 `naru.css`를 사용합니다. 스타일을 변경하려면 사이트의
`assets/naru.css` 또는 `static/assets/naru.css`를 제공하거나
`partial_head.html`을 직접 작성하세요.
`static/tools/`를 제공한다면 `index.html`도 필요합니다.

Markdown 콘텐츠의 front matter에는 `title`, `nav_title`, `slug`,
`description`, `published_date`, `updated_date`, `tags`가 필요합니다.
날짜는 `YYYY-MM-DD` 형식이며 `slug`는 소문자 kebab-case를 사용합니다.
소스 트리에서 직접 실행하려면 다음처럼 할 수 있습니다.

```powershell
$env:PYTHONPATH = "src"
python -m naru --version
```

## 개발 방향

- 템플릿과 페이지 구조의 유연성을 개선합니다.
- 설정과 렌더링의 결합을 줄여 다양한 사이트 구성을 지원합니다.
- 기본 템플릿과 사용 문서를 보강합니다.

상세한 경계와 모듈 책임은 [설계 문서](docs/architecture.md)를 참고하세요.
