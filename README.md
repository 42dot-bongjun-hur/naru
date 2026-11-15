# Naru

**콘텐츠는 각자, 생성기는 함께.**

Naru는 여러 사이트가 하나의 정적 사이트 생성 엔진을 공유하면서도 설정,
콘텐츠, 테마와 빌드 결과물은 각 프로젝트 안에서 독립적으로 관리하기 위한
Python 기반 생성기 프로젝트입니다.

> 0.1.1 시험판: 현재는 정해진 템플릿과 콘텐츠 구조를 사용합니다. 범용 테마와
> 자유로운 페이지 구조는 아직 지원하지 않습니다.

## 기능

- `naru.yml`을 이용한 사이트 설정과 출력 경로 분리
- Markdown과 YAML front matter를 이용한 글·페이지 생성
- 카테고리·태그 아카이브, RSS, sitemap, robots.txt 생성
- 정적 파일과 글에 첨부한 이미지 복사

## 프로젝트 구조

```text
naru/
├── .github/workflows/ci.yml
├── docs/                       # 설계 및 사용자 문서
├── examples/basic-site/        # 사이트 설정과 콘텐츠 예시
├── src/naru/                   # 설치 가능한 Python 패키지와 CLI
├── tests/                      # 자동화 테스트
├── pyproject.toml
└── README.md
```

## 설치

Python 3.11 이상과 Git이 필요합니다. GitHub의 고정 태그로 설치할 수 있습니다.

```powershell
python -m pip install "git+https://github.com/bjnhur/naru.git@v0.1.1"
```

PyPI에는 게시하지 않았습니다.

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
예제에는 빌드에 필요한 템플릿과 정적 파일이 포함되지 않아 그대로 빌드할 수
없습니다.

## 사이트 구조

현재 버전은 아래 디렉터리와 템플릿 파일을 사용합니다.

```text
my-site/
├── naru.yml
├── content/
│   ├── posts/                 # Markdown 글
│   ├── pages/                 # Markdown 페이지 (선택)
│   └── data/                  # JSON 카탈로그 (선택)
├── templates/
│   ├── template_index.html, template_post.html
│   ├── template_catalog.html, template_archive.html
│   └── partial_head.html, partial_googletag.html, partial_nav.html, partial_footer.html
├── static/
│   └── tools/index.html
└── assets/
```

Markdown 콘텐츠의 front matter에는 `title`, `nav_title`, `slug`,
`description`, `published_date`, `updated_date`, `tags`가 필요합니다.
날짜는 `YYYY-MM-DD` 형식이며 `slug`는 소문자 kebab-case를 사용합니다.
현재 HTML 렌더링은 정해진 템플릿과 페이지 구조를 전제로 하므로, 임의의
템플릿이나 테마가 그대로 동작한다고 보장하지 않습니다.

소스 트리에서 직접 실행하려면 다음처럼 할 수 있습니다.

```powershell
$env:PYTHONPATH = "src"
python -m naru --version
```

## 개발 방향

- 템플릿과 페이지 구조의 유연성을 개선합니다.
- 설정과 렌더링의 결합을 줄여 다양한 사이트 구성을 지원합니다.
- 완전하게 빌드할 수 있는 예제와 사용 문서를 보강합니다.

상세한 경계와 모듈 책임은 [설계 문서](docs/architecture.md)를 참고하세요.
