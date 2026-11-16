import re
from datetime import date


def normalize_date(value, field_name: str, source_name: str) -> str:
    date_value = str(value or "").strip()
    if not date_value:
        raise ValueError(f"{source_name}: missing {field_name}")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_value):
        raise ValueError(
            f"{source_name}: {field_name} must use YYYY-MM-DD, got {date_value!r}"
        )
    try:
        parsed_date = date.fromisoformat(date_value)
    except ValueError as error:
        raise ValueError(
            f"{source_name}: {field_name} must use YYYY-MM-DD, got {date_value!r}"
        ) from error
    return parsed_date.isoformat()


def normalize_metadata(raw: dict, source_name: str) -> dict:
    metadata = dict(raw)
    legacy_fields = {"desc", "date", "keywords", "last_checked", "updated_note"}
    found_legacy_fields = legacy_fields.intersection(metadata)
    if found_legacy_fields:
        names = ", ".join(sorted(found_legacy_fields))
        raise ValueError(f"{source_name}: legacy metadata fields are not supported: {names}")

    for field_name in ("title", "nav_title", "slug"):
        if not isinstance(metadata.get(field_name), str) or not metadata[field_name].strip():
            raise ValueError(f"{source_name}: {field_name} is required")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", metadata["slug"]):
        raise ValueError(f"{source_name}: slug must be lowercase kebab-case")

    description = metadata.get("description")
    if not isinstance(description, str) or not description.strip():
        raise ValueError(f"{source_name}: description is required")
    metadata["description"] = description.strip()
    metadata["published_date"] = normalize_date(
        metadata.get("published_date"),
        "published_date",
        source_name,
    )
    metadata["updated_date"] = normalize_date(
        metadata.get("updated_date"),
        "updated_date",
        source_name,
    )
    if metadata["updated_date"] < metadata["published_date"]:
        raise ValueError(f"{source_name}: updated_date precedes published_date")

    tags = metadata.get("tags")
    if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
        raise ValueError(f"{source_name}: tags must be a list of strings")
    metadata["tags"] = [tag.strip() for tag in tags if tag.strip()]

    if "category" in metadata:
        category = metadata["category"]
        if not isinstance(category, str) or not category.strip():
            raise ValueError(f"{source_name}: category must be a non-empty string")
        metadata["category"] = category.strip()

    links_checked_date = metadata.get("links_checked_date", "")
    metadata["links_checked_date"] = (
        normalize_date(links_checked_date, "links_checked_date", source_name)
        if links_checked_date
        else ""
    )
    return metadata


def content_sort_key(item: dict) -> tuple[str, str, str]:
    return (
        item.get("updated_date", ""),
        item.get("published_date", ""),
        item.get("slug", ""),
    )


def keyword_content(tags: list[str]) -> str:
    return ", ".join(tags)
