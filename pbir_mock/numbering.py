from __future__ import annotations

from copy import deepcopy

from pbir_mock.models import Page, Visual


DEFAULT_EXCLUDED_TYPES = {"textbox", "basicshape", "image"}


def parse_type_filters(values: list[str] | None) -> set[str]:
    if not values:
        return set()
    parsed: set[str] = set()
    for value in values:
        for chunk in value.split(","):
            t = chunk.strip().lower()
            if t:
                parsed.add(t)
    return parsed


def include_visual(visual_type: str, include_types: set[str], exclude_types: set[str]) -> bool:
    normalized = visual_type.lower()
    if include_types and normalized not in include_types:
        return False
    if normalized in exclude_types:
        return False
    return True


def build_numbered_pages(
    pages: list[Page],
    *,
    numbering_scope: str = "page",
    include_types: set[str] | None = None,
    exclude_types: set[str] | None = None,
) -> list[Page]:
    include = include_types or set()
    exclude = exclude_types or set()
    numbered_pages: list[Page] = deepcopy(pages)

    report_seq = 1
    for page in numbered_pages:
        ordered = sorted(page.visuals, key=lambda v: (v.z, v.y, v.x, v.visual_id))
        selected: list[Visual] = []
        page_seq = 1

        for visual in ordered:
            if not include_visual(visual.visual_type, include, exclude):
                continue
            if numbering_scope == "report":
                seq = report_seq
                report_seq += 1
            else:
                seq = page_seq
                page_seq += 1

            visual.seq = seq
            title_or_id = visual.title or visual.visual_id
            visual.label = f"{page.page_name_safe} | {visual.visual_type} | {title_or_id} (V{seq:03d})"
            selected.append(visual)

        page.visuals = selected

    return numbered_pages

