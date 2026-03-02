from __future__ import annotations

from itertools import combinations
from urllib.parse import urlparse

from pbir_mock.models import Bookmark, Page, Visual


def _intersects(a: Visual, b: Visual) -> bool:
    ax2 = a.x + a.width
    ay2 = a.y + a.height
    bx2 = b.x + b.width
    by2 = b.y + b.height
    return a.x < bx2 and ax2 > b.x and a.y < by2 and ay2 > b.y


def validate_off_canvas(pages: list[Page]) -> list[dict[str, object]]:
    issues: list[dict[str, object]] = []
    for page in pages:
        for v in page.visuals:
            off_left = v.x < 0
            off_top = v.y < 0
            off_right = (v.x + v.width) > page.width
            off_bottom = (v.y + v.height) > page.height
            if off_left or off_top or off_right or off_bottom:
                issues.append(
                    {
                        "page_id": page.page_id,
                        "page_name": page.page_name,
                        "visual_id": v.visual_id,
                        "x": v.x,
                        "y": v.y,
                        "width": v.width,
                        "height": v.height,
                        "page_width": page.width,
                        "page_height": page.height,
                        "off_left": off_left,
                        "off_top": off_top,
                        "off_right": off_right,
                        "off_bottom": off_bottom,
                    }
                )
    return issues


def validate_overlaps(pages: list[Page]) -> list[dict[str, object]]:
    overlaps: list[dict[str, object]] = []
    for page in pages:
        for a, b in combinations(sorted(page.visuals, key=lambda it: it.seq), 2):
            if _intersects(a, b):
                overlaps.append(
                    {
                        "page_id": page.page_id,
                        "page_name": page.page_name,
                        "visual_id_a": a.visual_id,
                        "visual_id_b": b.visual_id,
                        "seq_a": a.seq,
                        "seq_b": b.seq,
                    }
                )
    return overlaps


def validate_bookmark_references(pages: list[Page], bookmarks: list[Bookmark]) -> list[dict[str, object]]:
    issues: list[dict[str, object]] = []
    page_by_id = {p.page_id: p for p in pages}

    for bookmark in bookmarks:
        if bookmark.active_section not in page_by_id:
            issues.append(
                {
                    "bookmark_file": bookmark.bookmark_file,
                    "bookmark_name": bookmark.bookmark_name,
                    "active_section": bookmark.active_section,
                    "issue_type": "missing_active_section",
                    "missing_id": bookmark.active_section,
                }
            )
            continue

        page = page_by_id[bookmark.active_section]
        valid_visual_ids = {v.visual_id for v in page.visuals}
        for visual_id in bookmark.section_visual_ids:
            if visual_id not in valid_visual_ids:
                issues.append(
                    {
                        "bookmark_file": bookmark.bookmark_file,
                        "bookmark_name": bookmark.bookmark_name,
                        "active_section": bookmark.active_section,
                        "issue_type": "missing_visual_reference",
                        "missing_id": visual_id,
                    }
                )
    return issues


def validate_navigation_links(
    pages: list[Page],
    bookmarks: list[Bookmark],
    button_links: list[dict[str, str]],
) -> list[dict[str, object]]:
    page_ids = {p.page_id for p in pages}
    bookmark_ids = {b.bookmark_name for b in bookmarks}
    rows: list[dict[str, object]] = []

    for link in button_links:
        link_type = (link.get("link_type") or "").lower()
        target = ""
        status = "ok"
        issue = ""

        if link_type == "pagenavigation":
            target = link.get("navigation_section", "")
            if target not in page_ids:
                status = "error"
                issue = "missing_page_target"
        elif link_type == "bookmark":
            target = link.get("bookmark", "")
            if target not in bookmark_ids:
                status = "error"
                issue = "missing_bookmark_target"
        elif link_type == "weburl":
            target = link.get("web_url", "")
            parsed = urlparse(target)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                status = "error"
                issue = "invalid_web_url"
        elif link_type == "back":
            status = "ok"
            issue = "back_navigation"
        else:
            status = "warn"
            issue = "unknown_or_missing_link_type"

        rows.append(
            {
                "page_id": link.get("page_id", ""),
                "visual_id": link.get("visual_id", ""),
                "link_type": link.get("link_type", ""),
                "target": target,
                "status": status,
                "issue": issue,
            }
        )
    return rows


def validate_click_block_risks(
    pages: list[Page],
    button_links: list[dict[str, str]],
) -> list[dict[str, object]]:
    button_ids = {(row.get("page_id", ""), row.get("visual_id", "")) for row in button_links}
    risks: list[dict[str, object]] = []

    for page in pages:
        visuals = page.visuals
        for button in visuals:
            if button.visual_type != "actionButton":
                continue
            if (page.page_id, button.visual_id) not in button_ids:
                continue
            for other in visuals:
                if other.visual_id == button.visual_id:
                    continue
                if other.z <= button.z:
                    continue
                if _intersects(button, other):
                    risks.append(
                        {
                            "page_id": page.page_id,
                            "page_name": page.page_name,
                            "button_visual_id": button.visual_id,
                            "button_z": button.z,
                            "blocking_visual_id": other.visual_id,
                            "blocking_type": other.visual_type,
                            "blocking_z": other.z,
                        }
                    )
    return risks
