from __future__ import annotations

from pathlib import Path
from typing import Any

from pbir_mock.discovery import discover_bookmark_files
from pbir_mock.models import Bookmark
from pbir_mock.utils import read_json


def _section_visual_ids(payload: dict[str, Any], active_section: str) -> list[str]:
    sections = payload.get("explorationState", {}).get("sections", {})
    if not isinstance(sections, dict):
        return []
    active = sections.get(active_section, {})
    if not isinstance(active, dict):
        return []
    visual_containers = active.get("visualContainers", {})
    if not isinstance(visual_containers, dict):
        return []
    return list(visual_containers.keys())


def parse_bookmarks(definition_dir: Path) -> list[Bookmark]:
    bookmarks: list[Bookmark] = []
    for bookmark_file in discover_bookmark_files(definition_dir):
        payload = read_json(bookmark_file)
        active_section = str(payload.get("explorationState", {}).get("activeSection", ""))
        bookmarks.append(
            Bookmark(
                bookmark_file=bookmark_file.name,
                bookmark_name=str(payload.get("name", bookmark_file.stem)),
                display_name=str(payload.get("displayName", payload.get("name", bookmark_file.stem))),
                active_section=active_section,
                section_visual_ids=_section_visual_ids(payload, active_section),
            )
        )
    return bookmarks
