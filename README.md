# Naru

**콘텐츠는 각자, 생성기는 함께.**

Naru는 여러 사이트가 하나의 정적 사이트 생성 엔진을 공유하면서도 설정,
콘텐츠, 테마와 빌드 결과물은 각 프로젝트 안에서 독립적으로 관리하기 위한
Python 기반 생성기 프로젝트입니다.

> 0.1.0 시험판: 기존 `astro-paper` 엔진을 이식하고 devbj.com 설정을 사이트
> 프로젝트의 `naru.yml`로 분리했습니다. 운영 배포는 아직 기존 절차를 사용합니다.
> 범용 테마와 `ts.devbj.com` 지원은 아직 제공하지 않습니다.

## 목표

- 사이트별 설정과 콘텐츠를 분리하고 공통 빌드 엔진을 재사용합니다.
- Markdown 글을 정적 HTML로 생성해 별도 서버 없이 배포할 수 있게 합니다.
- URL, 메타데이터, RSS, sitemap 등 사이트별 차이를 명시적 설정으로 관리합니다.
- 생성 결과는 각 사이트 프로젝트에 기록해 서로 덮어쓰지 않도록 합니다.

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
python -m pip install "git+https://github.com/bjnhur/naru.git@v0.1.0"
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

사이트 빌드는 프로젝트 루트와 출력 디렉터리를 지정합니다.

```powershell
naru build --site-root "D:\NewGitHub\astro-paper" --output "D:\NewGitHub\naru\.naru-preview-v2"
```

사이트 루트의 `naru.yml`을 읽습니다. `--output`을 생략하면
`<site-root>/docs`를 사용합니다. 출력 폴더는 비어 있거나 같은 사이트의
Naru가 생성한 `.naru-output` 표식이 있어야 합니다. 기존 폴더를 자동으로
인수하지 않으므로 운영 전환 전에는 새 출력 경로로 검증하세요. Naru가 관리하는
출력 폴더의 HTML과 일부 정적 파일은 빌드할 때 정리·교체하므로, 직접 작성한
파일을 그곳에 두지 마세요. 설정 예시는 `examples/basic-site/naru.yml`입니다.
현재 엔진은 devbj.com의 템플릿과 콘텐츠 구조가 필요하며, 예제는 아직 완전한
빌드 가능 사이트가 아닙니다.

소스 트리에서 직접 실행하려면 다음처럼 할 수 있습니다.

```powershell
$env:PYTHONPATH = "src"
python -m naru --version
```

## 다음 단계

1. devbj.com 배포 워크플로를 고정된 Naru 버전으로 전환합니다.
2. devbj.com 전용 렌더링을 분리하고 ts.devbj.com 호환성을 검증합니다.
3. 전환을 확인한 후 사이트 안의 기존 엔진을 제거합니다.

상세한 경계와 모듈 책임은 [설계 문서](docs/architecture.md)를 참고하세요.
