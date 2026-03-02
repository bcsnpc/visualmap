from __future__ import annotations

import csv
from pathlib import Path

from pbir_mock.utils import ensure_dir


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def export_validation(
    out_root: Path,
    off_canvas_rows: list[dict[str, object]],
    overlap_rows: list[dict[str, object]],
    bookmark_rows: list[dict[str, object]],
    navigation_rows: list[dict[str, object]],
    click_block_rows: list[dict[str, object]],
) -> None:
    validation_root = out_root / "validation"
    ensure_dir(validation_root)

    _write_csv(
        validation_root / "off_canvas.csv",
        off_canvas_rows,
        [
            "page_id",
            "page_name",
            "visual_id",
            "x",
            "y",
            "width",
            "height",
            "page_width",
            "page_height",
            "off_left",
            "off_top",
            "off_right",
            "off_bottom",
        ],
    )
    _write_csv(
        validation_root / "overlaps.csv",
        overlap_rows,
        ["page_id", "page_name", "visual_id_a", "visual_id_b", "seq_a", "seq_b"],
    )
    _write_csv(
        validation_root / "bookmark_references.csv",
        bookmark_rows,
        ["bookmark_file", "bookmark_name", "active_section", "issue_type", "missing_id"],
    )
    _write_csv(
        validation_root / "navigation_report.csv",
        navigation_rows,
        ["page_id", "visual_id", "link_type", "target", "status", "issue"],
    )
    _write_csv(
        validation_root / "click_block_risks.csv",
        click_block_rows,
        [
            "page_id",
            "page_name",
            "button_visual_id",
            "button_z",
            "blocking_visual_id",
            "blocking_type",
            "blocking_z",
        ],
    )
