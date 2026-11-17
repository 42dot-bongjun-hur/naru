from __future__ import annotations

import io
import tempfile
import unicodedata
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from urllib.parse import quote

import yaml

from naru.config import BuildConfig, load_config
from naru.engine.config import use_config
from naru.engine.loader import (
    load_all_contents,
    load_catalog_sites,
    load_markdown_contents,
)
from naru.engine.routes import content_output_path, content_path


class MarkdownContentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.posts = Path(self.temp.name) / "posts"
        self.posts.mkdir()
        site_root = Path(__file__).resolve().parents[1] / "examples" / "basic-site"
        config = BuildConfig(
            site_root,
            Path(self.temp.name) / "output",
            load_config(
                site_root / "naru.yml",
                overrides={"site_origin": "https://example.com"},
            ),
        )
        self.enterContext(use_config(config))

    def write_post(self, body: str) -> Path:
        source = self.posts / "example.md"
        source.write_text(body, encoding="utf-8")
        return source

    def test_pymdown_syntax_and_korean_heading_are_rendered(self) -> None:
        self.write_post(
            "---\n"
            "title: 문법 예제\n"
            "nav_title: 문법 예제\n"
            "slug: syntax-example\n"
            "description: Markdown 문법 예제\n"
            "published_date: 2026-11-17\n"
            "updated_date: 2026-11-17\n"
            "tags: []\n"
            "---\n"
            "## 한글 제목\n\n"
            "- [x] 완료\n"
            "- [ ] 대기\n\n"
            "~~취소선~~ H~2~O\n\n"
            "````python\n"
            "print('한글')\n"
            "````\n"
        )

        item = load_markdown_contents(self.posts, "post")[0]

        self.assertIn('id="한글-제목"', item["html_content"])
        self.assertIn('type="checkbox"', item["html_content"])
        self.assertIn("<del>취소선</del>", item["html_content"])
        self.assertIn("H<sub>2</sub>O", item["html_content"])
        self.assertIn('<pre class="highlight">', item["html_content"])
        self.assertIn('class="language-python"', item["html_content"])

    def test_invalid_front_matter_reports_source_and_line(self) -> None:
        source = self.write_post(
            "---\n"
            "title: [broken\n"
            "---\n"
            "본문\n"
        )

        with self.assertRaises(ValueError) as error:
            load_markdown_contents(self.posts, "post")
        self.assertIn(f"{source}:2: invalid YAML front matter", str(error.exception))

    def test_front_matter_requires_exact_delimiter_lines(self) -> None:
        self.write_post("----\ntitle: invalid\n---\n본문\n")

        with self.assertRaisesRegex(ValueError, "missing YAML front matter"):
            load_markdown_contents(self.posts, "post")

    def test_post_category_defaults_to_first_folder(self) -> None:
        folder = self.posts / "blog" / "nested"
        folder.mkdir(parents=True)
        source = folder / "example.md"
        front_matter = (
            "---\ntitle: 예제\nnav_title: 예제\nslug: example\n"
            "description: 예제 글\npublished_date: 2026-11-17\n"
            "updated_date: 2026-11-17\ntags: []\n"
        )
        source.write_text(front_matter + "---\n본문\n", encoding="utf-8")
        item = load_markdown_contents(self.posts, "post")[0]
        self.assertEqual(item["meta"]["category"], "blog")

        source.write_text(
            front_matter + "category: bookmark\n---\n본문\n", encoding="utf-8"
        )
        item = load_markdown_contents(self.posts, "post")[0]
        self.assertEqual(item["meta"]["category"], "bookmark")

        source.write_text(front_matter + "---\n본문\n", encoding="utf-8")
        item = load_markdown_contents(self.posts, "page")[0]
        self.assertNotIn("category", item["meta"])

    def test_catalog_category_defaults_to_folder(self) -> None:
        folder = self.posts / "resources"
        folder.mkdir()
        (folder / "example.md").write_text(
            "---\nlayout: catalog\ntitle: 목록\nnav_title: 목록\n"
            "slug: example\ndescription: 사이트 목록\n"
            "published_date: 2026-11-17\nupdated_date: 2026-11-17\n"
            "tags: []\n---\n본문\n",
            encoding="utf-8",
        )
        (folder / "example.sites.yml").write_text("[]\n", encoding="utf-8")
        item = load_markdown_contents(self.posts, "post")[0]
        self.assertEqual(item["meta"]["category"], "resources")

    def test_duplicate_post_output_paths_are_rejected(self) -> None:
        content = (
            "---\ntitle: 예제\nnav_title: 예제\nslug: example\n"
            "description: 예제 글\npublished_date: 2026-11-17\n"
            "updated_date: 2026-11-17\ntags: []\n---\n본문\n"
        )
        first = self.posts / "blog" / "first.md"
        second = self.posts / "bookmark" / "second.md"
        for path in (first, second):
            path.parent.mkdir()
            path.write_text(content, encoding="utf-8")

        with self.assertRaises(ValueError) as error:
            load_all_contents(Path(self.temp.name) / "data", self.posts)
        self.assertIn("output path", str(error.exception))
        self.assertIn(str(first), str(error.exception))
        self.assertIn(str(second), str(error.exception))

    def test_local_image_urls_include_base_url(self) -> None:
        self.write_post(
            "---\ntitle: 예제\nnav_title: 예제\nslug: example\n"
            "description: 예제 글\npublished_date: 2026-11-17\n"
            "updated_date: 2026-11-17\ntags: []\n---\n"
            "![로컬](image.png?size=1#view)\n\n"
            "![정적](../static/shared.png)\n"
        )
        (self.posts / "image.png").write_bytes(b"image")
        static = Path(self.temp.name) / "static"
        static.mkdir()
        (static / "shared.png").write_bytes(b"image")
        example = Path(__file__).resolve().parents[1] / "examples" / "basic-site"
        for base_url in ("", "/notes"):
            with self.subTest(base_url=base_url):
                settings = load_config(
                    example / "naru.yml",
                    overrides={
                        "site_origin": "https://example.com", "base_url": base_url
                    },
                )
                config = BuildConfig(
                    Path(self.temp.name), Path(self.temp.name) / "out", settings
                )
                with use_config(config):
                    item = load_markdown_contents(self.posts, "post")[0]
                self.assertIn(
                    f'src="{base_url}/assets/posts/example/image.png?size=1#view"',
                    item["html_content"],
                )
                self.assertIn(f'src="{base_url}/shared.png"', item["html_content"])

    def test_relative_markdown_links_resolve_across_posts_and_pages(self) -> None:
        template = (
            "---\ntitle: 문서\nnav_title: 문서\nslug: {slug}\n"
            "description: 문서 설명\npublished_date: 2026-11-17\n"
            "updated_date: 2026-11-17\ntags: []\n---\n{body}\n"
        )
        pages = Path(self.temp.name) / "pages"
        pages.mkdir()
        (self.posts / "a.md").write_text(
            template.format(
                slug="first",
                body="[글](b.md?view=1#한글) [페이지](../pages/info.md) "
                "[외부](https://other.example/b.md)",
            ),
            encoding="utf-8",
        )
        (self.posts / "b.md").write_text(
            template.format(slug="different-slug", body="본문"), encoding="utf-8"
        )
        (pages / "info.md").write_text(
            template.format(slug="about", body="[글](../posts/a.md#part)"),
            encoding="utf-8",
        )
        example = Path(__file__).resolve().parents[1] / "examples" / "basic-site"
        settings = load_config(
            example / "naru.yml",
            overrides={"site_origin": "https://example.com", "base_url": "/notes"},
        )
        config = BuildConfig(
            Path(self.temp.name), Path(self.temp.name) / "out", settings
        )
        with use_config(config):
            items = load_all_contents(Path(self.temp.name) / "data", self.posts, pages)
        by_slug = {item["slug"]: item for item in items}
        self.assertIn(
            'href="/notes/posts/different-slug/?view=1#한글"',
            by_slug["first"]["html_content"],
        )
        self.assertIn('href="/notes/about/"', by_slug["first"]["html_content"])
        self.assertIn(
            'href="https://other.example/b.md"', by_slug["first"]["html_content"]
        )
        self.assertIn(
            'href="/notes/posts/first/#part"', by_slug["about"]["html_content"]
        )

    def test_missing_relative_markdown_link_reports_source(self) -> None:
        source = self.write_post(
            "---\ntitle: 문서\nnav_title: 문서\nslug: example\n"
            "description: 문서 설명\npublished_date: 2026-11-17\n"
            "updated_date: 2026-11-17\ntags: []\n---\n"
            "[없음](missing.md#section)\n"
        )
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            items = load_all_contents(Path(self.temp.name) / "data", self.posts)
        self.assertIn("[WARNING]", stderr.getvalue())
        self.assertIn(str(source), stderr.getvalue())
        self.assertIn("missing.md#section", stderr.getvalue())
        self.assertIn('href="missing.md#section"', items[0]["html_content"])

    def test_drafts_and_future_posts_require_explicit_inclusion(self) -> None:
        template = (
            "---\ntitle: 문서\nnav_title: 문서\nslug: {slug}\n"
            "description: 설명\npublished_date: {date}\n"
            "updated_date: {date}\ntags: []\n{extra}---\n본문\n"
        )
        for slug, date, extra in (
            ("published", "2020-01-01", ""),
            ("draft", "2020-01-01", "draft: true\n"),
            ("future", "9999-01-01", ""),
            ("future-draft", "9999-01-01", "draft: true\n"),
        ):
            (self.posts / f"{slug}.md").write_text(
                template.format(slug=slug, date=date, extra=extra), encoding="utf-8"
            )
        data_dir = Path(self.temp.name) / "data"
        for drafts, future, expected in (
            (False, False, {"published"}),
            (True, False, {"published", "draft"}),
            (False, True, {"published", "future"}),
            (True, True, {"published", "draft", "future", "future-draft"}),
        ):
            with self.subTest(drafts=drafts, future=future):
                items = load_all_contents(
                    data_dir, self.posts, include_drafts=drafts, include_future=future
                )
                self.assertEqual({item["slug"] for item in items}, expected)

        (self.posts / "draft.md").write_text(
            template.format(slug="draft", date="2020-01-01", extra="draft: 'true'\n"),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "draft must be true or false"):
            load_all_contents(data_dir, self.posts)

    def test_korean_slug_is_normalized_and_url_encoded(self) -> None:
        slug = unicodedata.normalize("NFD", "한글-문서")
        self.write_post(
            "---\ntitle: 문서\nnav_title: 문서\n"
            f"slug: {slug}\n"
            "description: 설명\npublished_date: 2020-01-01\n"
            "updated_date: 2020-01-01\n"
            f"category: {unicodedata.normalize('NFD', '개발')}\n"
            f"tags: [{unicodedata.normalize('NFD', '한글')}]\n---\n본문\n"
        )
        item = load_all_contents(Path(self.temp.name) / "data", self.posts)[0]
        self.assertEqual(item["slug"], "한글-문서")
        self.assertEqual(item["meta"]["category"], "개발")
        self.assertEqual(item["tags"], ["한글"])
        self.assertEqual(content_path(item), f"/posts/{quote('한글-문서')}/")
        self.assertEqual(content_output_path(item).parts[-2], "한글-문서")

    def test_equivalent_korean_slugs_are_rejected(self) -> None:
        template = (
            "---\ntitle: 문서\nnav_title: 문서\nslug: {slug}\n"
            "description: 설명\npublished_date: 2020-01-01\n"
            "updated_date: 2020-01-01\ntags: []\n---\n본문\n"
        )
        (self.posts / "first.md").write_text(
            template.format(slug="한글"), encoding="utf-8"
        )
        (self.posts / "second.md").write_text(
            template.format(slug=unicodedata.normalize("NFD", "한글")),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "conflicts"):
            load_all_contents(Path(self.temp.name) / "data", self.posts)

    def test_catalog_loads_matching_sites_file(self) -> None:
        self.write_post(
            "---\nlayout: catalog\ntitle: 목록\nnav_title: 목록\n"
            "slug: example\ndescription: 사이트 목록\n"
            "published_date: 2026-11-17\nupdated_date: 2026-11-17\n"
            "tags: []\n---\n\n소개입니다.\n"
        )
        (self.posts / "example.sites.yml").write_text(
            "- id: naru\n  name: 나루\n  url: https://example.com/\n"
            "  description: 한글 사이트\n",
            encoding="utf-8",
        )

        item = load_markdown_contents(self.posts, "post")[0]
        self.assertEqual(item["raw_data"]["sites"][0]["name"], "나루")
        self.assertIn("소개입니다.", item["markdown_intro_html"])

    def test_catalog_rejects_missing_or_invalid_sites_file(self) -> None:
        self.write_post(
            "---\nlayout: catalog\ntitle: 목록\nnav_title: 목록\n"
            "slug: example\ndescription: 사이트 목록\n"
            "published_date: 2026-11-17\nupdated_date: 2026-11-17\n"
            "tags: []\n---\n\n소개입니다.\n"
        )
        with self.assertRaisesRegex(ValueError, r"example\.sites\.yml"):
            load_markdown_contents(self.posts, "post")

        (self.posts / "example.sites.yml").write_text(
            "- id: naru\n  name: 나루\n  url: javascript:alert(1)\n"
            "  description: 한글 사이트\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, r"example\.sites\.yml.*item 1.*url"):
            load_markdown_contents(self.posts, "post")

    def test_catalog_validates_each_site(self) -> None:
        path = self.posts / "example.sites.yml"
        valid = {
            "id": "naru",
            "name": "나루",
            "url": "https://example.com/",
            "description": "한글 사이트",
        }
        cases = (
            ([{**valid, "name": ""}], "item 1: name"),
            ([{**valid, "id": "잘못된-id"}], "item 1: id"),
            ([valid, valid], "item 2: duplicate id"),
            ([{**valid, "url": "https://example.com:bad"}], "item 1: url"),
            ([{**valid, "status": ["active"]}], "item 1: status"),
            ([{**valid, "statuz": "active"}], "item 1: unknown fields"),
            ({"sites": []}, "catalog sites must be a list"),
        )
        for data, message in cases:
            with self.subTest(message=message):
                path.write_text(
                    yaml.safe_dump(data, allow_unicode=True), encoding="utf-8"
                )
                with self.assertRaises(ValueError) as error:
                    load_catalog_sites(path)
                self.assertIn(str(path), str(error.exception))
                self.assertIn(message, str(error.exception))

        path.write_text("[]\n", encoding="utf-8")
        self.assertEqual(load_catalog_sites(path), [])
        path.write_text("- id: [broken\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "cannot read catalog sites"):
            load_catalog_sites(path)

    def test_catalog_rejects_legacy_sources_with_migration_guidance(self) -> None:
        self.write_post("---\nlayout: catalog\nsites: []\n---\n")
        with self.assertRaisesRegex(ValueError, "move front matter sites"):
            load_markdown_contents(self.posts, "post")

        data_dir = Path(self.temp.name) / "data"
        data_dir.mkdir()
        (data_dir / "old.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, r"old\.json.*\.sites\.yml"):
            load_all_contents(data_dir, self.posts)


if __name__ == "__main__":
    unittest.main()