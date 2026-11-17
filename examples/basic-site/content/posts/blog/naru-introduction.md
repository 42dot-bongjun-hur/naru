---
title: Naru 소개
nav_title: Naru 소개
slug: naru-introduction
description: Markdown과 Python으로 한글 콘텐츠 사이트를 만드는 Naru를 소개합니다.
published_date: 2026-11-17
updated_date: 2026-11-17
tags:
  - naru
  - python
  - static-site
---

# Naru 소개

Naru는 Markdown으로 작성한 글과 페이지를 정적 HTML 사이트로 만드는 Python
생성기입니다. 사이트의 콘텐츠와 설정은 각 프로젝트에서 관리하고, Naru는
그 파일을 읽어 배포할 결과물을 생성합니다. 블로그나 개인 기록처럼 한글 글을
꾸준히 작성하는 사이트를 간단하게 운영하는 것이 목표입니다.

## 어떤 기능이 있나요?

- Markdown 글과 일반 페이지, 링크를 모아 보여 주는 카탈로그를 만듭니다.
- 글을 폴더와 카테고리, 태그로 정리하고 RSS와 사이트맵을 생성합니다.
- 한글 제목 앵커와 슬러그를 지원하고 로컬 이미지와 상대 Markdown 링크를 처리합니다.
- Jinja2 템플릿과 스타일을 사이트별로 덮어쓸 수 있습니다.
- 초안과 미래 날짜의 글은 기본 빌드에서 제외합니다.

이 사이트는 개발 중인 Naru를 사용합니다. 위 기능 중 일부는 현재 PyPI에 게시된
`0.2.0`에 아직 포함되지 않았으므로 설치한 버전의 문서를 확인하세요.

## 시작하기

Python 3.11 이상에서 패키지를 설치합니다.

```powershell
python -m pip install naru-sitegen
```

사이트 폴더에 다음 설정 파일을 만들고 사이트 이름과 실제 게시할 도메인을 지정합니다.

```yaml
# naru.yml
site_name: 나의 기록
site_origin: https://example.com
```

`content/posts/` 아래에 YAML front matter와 Markdown 본문을 작성한 뒤 빌드합니다.
게시물 작성 예시는 [Markdown 기본 문법](welcome.md)에서 확인할 수 있습니다.

```powershell
naru build --site-root . --output _site
```

생성된 `_site` 폴더는 GitHub Pages 등 정적 호스팅에 배포할 수 있습니다.
`site_origin`은 예제 주소가 아닌 직접 관리하는 실제 게시 주소로 바꿔야 합니다.

## 더 알아보기

- [Naru GitHub 저장소](https://github.com/bjnhur/naru)
- [PyPI 패키지](https://pypi.org/project/naru-sitegen/)
- [Python 정적 사이트 생성기 모음](../bookmark/python-ssg.md)