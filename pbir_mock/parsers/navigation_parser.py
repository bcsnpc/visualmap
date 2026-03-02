from __future__ import annotations

from pathlib import Path

from pbir_mock.discovery import discover_visual_files
from pbir_mock.utils import extract_literal_value, read_json


def parse_button_links(definition_dir: Path, page_ids: list[str]) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for page_id in page_ids:
        for visual_file in discover_visual_files(definition_dir, page_id):
            payload = read_json(visual_file)
            visual = payload.get("visual", {})
            if visual.get("visualType") != "actionButton":
                continue
            visual_id = str(payload.get("name", visual_file.parent.name))
            link_props = (
                visual.get("visualContainerObjects", {})
                .get("visualLink", [{}])[0]
                .get("properties", {})
            )
            link_type = extract_literal_value(link_props, ["type", "expr", "Literal", "Value"])
            navigation_section = extract_literal_value(link_props, ["navigationSection", "expr", "Literal", "Value"])
            bookmark = extract_literal_value(link_props, ["bookmark", "expr", "Literal", "Value"])
            web_url = extract_literal_value(link_props, ["webUrl", "expr", "Literal", "Value"])

            links.append(
                {
                    "page_id": page_id,
                    "visual_id": visual_id,
                    "link_type": link_type,
                    "navigation_section": navigation_section,
                    "bookmark": bookmark,
                    "web_url": web_url,
                }
            )
    return links

