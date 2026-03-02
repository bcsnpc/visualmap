from __future__ import annotations

from pathlib import Path


def discover_page_ids(definition_dir: Path) -> list[str]:
    pages_root = definition_dir / "pages"
    ids: list[str] = []
    for child in sorted(pages_root.iterdir()):
        if not child.is_dir():
            continue
        if (child / "page.json").exists():
            ids.append(child.name)
    return ids


def discover_visual_files(definition_dir: Path, page_id: str) -> list[Path]:
    visuals_root = definition_dir / "pages" / page_id / "visuals"
    if not visuals_root.exists():
        return []
    return sorted(visuals_root.glob("*/visual.json"))


def discover_bookmark_files(definition_dir: Path) -> list[Path]:
    bookmarks_root = definition_dir / "bookmarks"
    if not bookmarks_root.exists():
        return []
    return sorted(bookmarks_root.glob("*.bookmark.json"))

