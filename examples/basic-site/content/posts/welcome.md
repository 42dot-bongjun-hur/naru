---
title: Markdown 기본 문법
nav_title: Markdown 예제
slug: markdown-basics
description: 제목, 강조, 링크, 목록, 코드 블록을 사용하는 기본 글입니다.
published_date: 2026-11-16
updated_date: 2026-11-16
category: blog
tags:
  - markdown
  - blog
---

# Markdown으로 글 쓰기

Naru 블로그 글은 Markdown 파일로 작성합니다. 파일 맨 위의 YAML front matter에
제목, 주소 슬러그, 날짜, 카테고리와 태그를 지정하면 Naru가 페이지를 만듭니다.

## 글자 강조

굵은 글씨는 **두 개의 별표**로, 기울임은 *별표 하나*로 표시합니다.
`인라인 코드`도 쓸 수 있습니다.

## 목록과 링크

- Markdown 문법을 간단히 소개합니다.
- 블로그 글은 `blog` 카테고리에 모입니다.

[Python SSG 북마크 모음](/posts/python-ssg/)도 확인해 보세요.

## 코드 블록

```python
def greet(name):
    return f"Hello, {name}!"
```
