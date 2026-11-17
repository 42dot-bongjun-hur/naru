---
layout: catalog
title: Python 정적 사이트 생성기(SSG) 모음
nav_title: Python SSG
slug: python-ssg
description: Python 생태계의 정적 사이트 및 문서 생성기를 소개합니다.
published_date: 2026-11-16
updated_date: 2026-11-16
links_checked_date: 2026-11-16
maintenance_note: 2026-11-16 공식 사이트 링크와 프로젝트 소개를 확인했습니다.
tags:
  - python
  - ssg
  - static-site
  - documentation
---

Python 생태계에서 사용할 수 있는 정적 사이트 생성기와 문서 도구를 모았습니다.
각 도구의 이름과 주소, 주요 특징은 같은 북마크 카탈로그 표 형식으로 정리합니다.

## Naru: 간단한 한국어 친화 정적 사이트 생성기

Naru는 Markdown으로 글과 페이지를 작성해 정적 사이트를 만드는 Python 도구입니다.
기본 설정과 템플릿으로 시작할 수 있고, 꼭 필요한 기능을 간단히 제공합니다.

- [Naru 소개 및 예제 사이트](https://naru.devbj.com/)
- [GitHub 저장소](https://github.com/bjnhur/naru)
- [PyPI 패키지와 설치 정보](https://pypi.org/project/naru-sitegen/)

설치는 `python -m pip install naru-sitegen`으로 할 수 있습니다.

## 용도에 따라 선택하기

블로그와 일반 콘텐츠 사이트에는 Pelican 또는 Nikola를 살펴보세요. 구조화된
콘텐츠 모델과 편집 UI가 필요하면 Lektor가 적합할 수 있습니다.

## 문서 도구 안내

MkDocs와 Sphinx는 프로젝트 문서 사이트에 초점을 둡니다. Sphinx는 HTML 외에도
PDF용 LaTeX와 ePub 등 여러 형식으로 문서를 빌드할 수 있습니다.
