"""Load and validate the legacy engine's site-specific settings."""

import re
from pathlib import Path
from urllib.parse import urlsplit

import yaml

STRING_FIELDS = {
    "site_name",
    "site_origin",
    "site_slogan_en",
    "site_slogan_ko",
    "site_tagline",
    "site_description",
    "base_url",
    "posts_url_prefix",
    "category_url_prefix",
    "tag_url_prefix",
    "rss_title",
    "rss_description",
    "adsense_pub_id",
    "ad_slot_top",
    "ad_slot_mid",
    "ad_slot_side",
    "author_name",
    "author_bio",
    "author_note_default",
}
NONEMPTY_FIELDS = {
    "site_name",
    "site_origin",
    "site_tagline",
    "site_description",
    "posts_url_prefix",
    "category_url_prefix",
    "tag_url_prefix",
    "rss_title",
    "rss_description",
}
POSITIVE_FIELDS = {
    "posts_per_page",
    "rss_item_limit",
    "home_posts_per_category",
    "home_recent_posts",
    "inline_ad_chars",
}
NONNEGATIVE_FIELDS = {"home_max_ads", "inline_ad_max"}
MAPPING_FIELDS = {"category_labels", "category_redirects", "author_notes"}
LIST_FIELDS = {"home_category_order", "home_category_groups"}
FIELDS = (
    STRING_FIELDS | POSITIVE_FIELDS | NONNEGATIVE_FIELDS | MAPPING_FIELDS | LIST_FIELDS
)


class ConfigError(ValueError):
    """A site configuration is missing or invalid."""


def load_config(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8-sig") as source:
            data = yaml.safe_load(source)
    except (OSError, yaml.YAMLError) as error:
        raise ConfigError(f"{path}: cannot read site configuration: {error}") from error
    if not isinstance(data, dict) or any(not isinstance(key, str) for key in data):
        raise ConfigError(
            f"{path}: site configuration must be a mapping with string keys"
        )
    missing, unknown = FIELDS - data.keys(), data.keys() - FIELDS
    if missing or unknown:
        details = []
        if missing:
            details.append(f"missing fields: {', '.join(sorted(missing))}")
        if unknown:
            details.append(f"unknown fields: {', '.join(sorted(unknown))}")
        raise ConfigError(f"{path}: {'; '.join(details)}")
    for field in STRING_FIELDS:
        if not isinstance(data[field], str) or (
            field in NONEMPTY_FIELDS and not data[field].strip()
        ):
            raise ConfigError(f"{path}: {field} must be a valid string")
    for field in POSITIVE_FIELDS | NONNEGATIVE_FIELDS:
        value = data[field]
        minimum = 1 if field in POSITIVE_FIELDS else 0
        if type(value) is not int or value < minimum:
            raise ConfigError(f"{path}: {field} must be an integer >= {minimum}")
    for field in MAPPING_FIELDS:
        value = data[field]
        if not isinstance(value, dict) or any(
            not isinstance(k, str) or not isinstance(v, str) for k, v in value.items()
        ):
            raise ConfigError(f"{path}: {field} must map strings to strings")
    for old, new in data["category_redirects"].items():
        if not all(
            re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) for slug in (old, new)
        ):
            raise ConfigError(
                f"{path}: category_redirects must use lowercase kebab-case slugs"
            )
    order = data["home_category_order"]
    if not isinstance(order, list) or any(not isinstance(item, str) for item in order):
        raise ConfigError(f"{path}: home_category_order must be a list of strings")
    groups = data["home_category_groups"]
    if not isinstance(groups, list) or any(
        not isinstance(group, list)
        or len(group) != 4
        or any(not isinstance(group[i], str) for i in (0, 1, 3))
        or not isinstance(group[2], list)
        or any(not isinstance(category, str) for category in group[2])
        for group in groups
    ):
        raise ConfigError(
            f"{path}: home_category_groups must contain "
            "[label, subtitle, categories, icon]"
        )
    try:
        origin = urlsplit(data["site_origin"])
        if (
            origin.scheme not in {"http", "https"}
            or not origin.hostname
            or origin.username
            or origin.password
            or origin.path
            or origin.query
            or origin.fragment
        ):
            raise ValueError
    except ValueError as error:
        raise ConfigError(
            f"{path}: site_origin must be an HTTP(S) origin without a path"
        ) from error
    for field in (
        "base_url",
        "posts_url_prefix",
        "category_url_prefix",
        "tag_url_prefix",
    ):
        value = data[field]
        if value and not re.fullmatch(r"/[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*", value):
            raise ConfigError(
                f"{path}: {field} must be an absolute URL path without a trailing slash"
            )
    return data
