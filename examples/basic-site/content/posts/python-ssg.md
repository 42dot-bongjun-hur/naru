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
category: bookmark
tags:
  - python
  - ssg
  - static-site
  - documentation
sites:
  - id: pelican
    name: Pelican
    url: https://getpelican.com/
    description: >-
      Python으로 작성된 정적 사이트 생성기입니다. Markdown과 reStructuredText로
      글과 페이지를 만들고 테마, 플러그인, RSS·Atom 피드를 사용할 수 있습니다.
    status: active
  - id: lektor
    name: Lektor
    url: https://www.getlektor.com/
    description: >-
      구조화된 파일 기반 콘텐츠와 관리자 UI를 제공하는 Python 기반 CMS 겸 정적
      사이트 생성기입니다. 사용자 정의 콘텐츠 모델과 플러그인을 지원합니다.
    status: active
  - id: nikola
    name: Nikola
    url: https://getnikola.com/
    description: >-
      Python 3 정적 사이트 생성기로 블로그, 페이지, 다국어 사이트를 만들 수
      있습니다. Markdown, reStructuredText, Jupyter Notebook 입력과 플러그인을
      지원합니다.
    status: active
  - id: mkdocs
    name: MkDocs
    url: https://www.mkdocs.org/
    description: >-
      Markdown 문서에서 프로젝트 문서 사이트를 생성하는 Python 도구입니다. YAML
      설정과 테마·플러그인 생태계를 제공합니다.
    status: active
  - id: sphinx
    name: Sphinx
    url: https://www.sphinx-doc.org/
    description: >-
      Python 프로젝트 문서에서 널리 쓰이는 문서 생성기입니다. reStructuredText와
      MyST Markdown을 입력으로 사용하며 HTML, LaTeX, ePub 등 여러 형식으로
      문서를 빌드합니다.
    status: active
---

Python 생태계에서 사용할 수 있는 정적 사이트 생성기와 문서 도구를 모았습니다.
각 도구의 이름과 주소, 주요 특징은 같은 북마크 카탈로그 표 형식으로 정리합니다.

## 용도에 따라 선택하기

블로그와 일반 콘텐츠 사이트에는 Pelican 또는 Nikola를 살펴보세요. 구조화된
콘텐츠 모델과 편집 UI가 필요하면 Lektor가 적합할 수 있습니다.

## 문서 도구 안내

MkDocs와 Sphinx는 프로젝트 문서 사이트에 초점을 둡니다. Sphinx는 HTML 외에도
PDF용 LaTeX와 ePub 등 여러 형식으로 문서를 빌드할 수 있습니다.
