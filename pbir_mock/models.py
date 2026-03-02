from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Visual:
    page_id: str
    page_name: str
    page_name_safe: str
    visual_id: str
    visual_type: str
    title: str
    x: float
    y: float
    width: float
    height: float
    z: float
    link_type: str = ""
    navigation_section: str = ""
    bookmark_target: str = ""
    web_url: str = ""
    is_hidden: bool = False
    seq: int = 0
    label: str = ""


@dataclass
class Page:
    page_id: str
    page_name: str
    page_name_safe: str
    width: float
    height: float
    source_path: Path
    visuals: list[Visual] = field(default_factory=list)


@dataclass
class Bookmark:
    bookmark_file: str
    bookmark_name: str
    display_name: str
    active_section: str
    section_visual_ids: list[str]
