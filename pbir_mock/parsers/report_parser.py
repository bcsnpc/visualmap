from __future__ import annotations

from pathlib import Path
from typing import Any

from pbir_mock.discovery import discover_page_ids, discover_visual_files
from pbir_mock.models import Page, Visual
from pbir_mock.utils import extract_literal_value, read_json, sanitize_name, strip_single_quotes


def _page_order(definition_dir: Path) -> list[str]:
    pages_json = definition_dir / "pages" / "pages.json"
    if not pages_json.exists():
        return []
    payload = read_json(pages_json)
    order = payload.get("pageOrder")
    if isinstance(order, list):
        return [str(x) for x in order]
    return []


def _extract_title(visual_payload: dict[str, Any]) -> str:
    try:
        value = (
            visual_payload["visual"]["visualContainerObjects"]["title"][0]["properties"]["text"]["expr"]["Literal"]["Value"]
        )
        if isinstance(value, str):
            return strip_single_quotes(value)
    except (KeyError, IndexError, TypeError):
        pass
    return ""


def _as_number(data: dict[str, Any], key: str) -> float:
    value = data.get(key, 0)
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _link_props(visual_payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return visual_payload["visual"]["visualContainerObjects"]["visualLink"][0]["properties"]
    except (KeyError, IndexError, TypeError):
        return {}


def parse_pages_and_visuals(definition_dir: Path) -> list[Page]:
    ordered_ids = _page_order(definition_dir)
    discovered_ids = discover_page_ids(definition_dir)

    page_ids: list[str] = []
    seen: set[str] = set()
    for pid in ordered_ids + discovered_ids:
        if pid not in seen:
            page_ids.append(pid)
            seen.add(pid)

    pages: list[Page] = []
    for page_id in page_ids:
        page_file = definition_dir / "pages" / page_id / "page.json"
        if not page_file.exists():
            continue
        page_payload = read_json(page_file)
        page_name = str(page_payload.get("displayName", page_id)).strip() or page_id
        page = Page(
            page_id=page_id,
            page_name=page_name,
            page_name_safe=sanitize_name(page_name),
            width=_as_number(page_payload, "width"),
            height=_as_number(page_payload, "height"),
            source_path=page_file,
        )

        for visual_file in discover_visual_files(definition_dir, page_id):
            visual_payload = read_json(visual_file)
            position = visual_payload.get("position", {})
            visual_id = str(visual_payload.get("name", visual_file.parent.name))
            visual_type = str(visual_payload.get("visual", {}).get("visualType", "unknown"))
            title = _extract_title(visual_payload)
            props = _link_props(visual_payload)
            page.visuals.append(
                Visual(
                    page_id=page.page_id,
                    page_name=page.page_name,
                    page_name_safe=page.page_name_safe,
                    visual_id=visual_id,
                    visual_type=visual_type,
                    title=title,
                    x=_as_number(position, "x"),
                    y=_as_number(position, "y"),
                    width=_as_number(position, "width"),
                    height=_as_number(position, "height"),
                    z=_as_number(position, "z"),
                    link_type=extract_literal_value(props, ["type", "expr", "Literal", "Value"]),
                    navigation_section=extract_literal_value(props, ["navigationSection", "expr", "Literal", "Value"]),
                    bookmark_target=extract_literal_value(props, ["bookmark", "expr", "Literal", "Value"]),
                    web_url=extract_literal_value(props, ["webUrl", "expr", "Literal", "Value"]),
                    is_hidden=bool(visual_payload.get("isHidden", False)),
                )
            )

        _assign_labels(page)
        pages.append(page)

    return pages


def _assign_labels(page: Page) -> None:
    ordered = sorted(page.visuals, key=lambda v: (v.z, v.y, v.x, v.visual_id))
    for idx, visual in enumerate(ordered, start=1):
        visual.seq = idx
        title_or_id = visual.title or visual.visual_id
        visual.label = f"{page.page_name_safe} | {visual.visual_type} | {title_or_id} (V{idx:03d})"
