from __future__ import annotations

import csv
from pathlib import Path

from pbir_mock.models import Page, Visual
from pbir_mock.utils import ensure_dir, safe_page_csv_name


def _visual_rows(visuals: list[Visual]) -> list[dict[str, object]]:
    return [
        {
            "page_id": v.page_id,
            "page_name": v.page_name,
            "page_name_safe": v.page_name_safe,
            "seq": v.seq,
            "visual_id": v.visual_id,
            "type": v.visual_type,
            "title": v.title,
            "label": v.label,
            "x": v.x,
            "y": v.y,
            "width": v.width,
            "height": v.height,
            "z": v.z,
        }
        for v in visuals
    ]


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def export_inventory(pages: list[Page], out_root: Path) -> None:
    inventory_root = out_root / "inventory"
    ensure_dir(inventory_root)

    page_rows = [
        {
            "page_id": p.page_id,
            "page_name": p.page_name,
            "page_name_safe": p.page_name_safe,
            "width": p.width,
            "height": p.height,
            "visual_count": len(p.visuals),
        }
        for p in pages
    ]
    _write_csv(
        inventory_root / "pages.csv",
        page_rows,
        ["page_id", "page_name", "page_name_safe", "width", "height", "visual_count"],
    )

    all_visuals = [v for p in pages for v in sorted(p.visuals, key=lambda it: it.seq)]
    visual_fieldnames = [
        "page_id",
        "page_name",
        "page_name_safe",
        "seq",
        "visual_id",
        "type",
        "title",
        "label",
        "x",
        "y",
        "width",
        "height",
        "z",
    ]
    _write_csv(inventory_root / "visuals.csv", _visual_rows(all_visuals), visual_fieldnames)

    seen_page_filenames: set[str] = set()
    for page in pages:
        per_page_filename = safe_page_csv_name(page.page_name_safe, seen_page_filenames)
        _write_csv(
            inventory_root / f"page_{per_page_filename}.csv",
            _visual_rows(sorted(page.visuals, key=lambda it: it.seq)),
            visual_fieldnames,
        )

