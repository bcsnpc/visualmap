from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

from pbir_mock.exporters.inventory import export_inventory
from pbir_mock.exporters.mock_viewer import export_mock_viewer
from pbir_mock.exporters.pdf_annotator import annotate_pdf
from pbir_mock.exporters.validation import export_validation
from pbir_mock.numbering import DEFAULT_EXCLUDED_TYPES, build_numbered_pages, parse_type_filters
from pbir_mock.parsers.bookmark_parser import parse_bookmarks
from pbir_mock.parsers.navigation_parser import parse_button_links
from pbir_mock.parsers.report_parser import parse_pages_and_visuals
from pbir_mock.utils import ensure_dir
from pbir_mock.validate import (
    validate_bookmark_references,
    validate_click_block_risks,
    validate_navigation_links,
    validate_off_canvas,
    validate_overlaps,
)


def _build(input_dir: Path, out_dir: Path, *, write_inventory: bool = True) -> None:
    pages = parse_pages_and_visuals(input_dir)
    bookmarks = parse_bookmarks(input_dir)
    if write_inventory:
        export_inventory(pages, out_dir)
    export_mock_viewer(pages, out_dir, bookmarks=bookmarks)
    print(f"Build complete. Parsed {len(pages)} pages.")


def _validate(input_dir: Path, out_dir: Path) -> None:
    pages = parse_pages_and_visuals(input_dir)
    bookmarks = parse_bookmarks(input_dir)
    button_links = parse_button_links(input_dir, [p.page_id for p in pages])

    off_canvas_rows = validate_off_canvas(pages)
    overlap_rows = validate_overlaps(pages)
    bookmark_rows = validate_bookmark_references(pages, bookmarks)
    navigation_rows = validate_navigation_links(pages, bookmarks, button_links)
    click_block_rows = validate_click_block_risks(pages, button_links)
    export_validation(out_dir, off_canvas_rows, overlap_rows, bookmark_rows, navigation_rows, click_block_rows)

    print(
        "Validation complete."
        f" off_canvas={len(off_canvas_rows)}, overlaps={len(overlap_rows)},"
        f" bookmark_issues={len(bookmark_rows)}, navigation_checks={len(navigation_rows)},"
        f" click_block_risks={len(click_block_rows)}"
    )


def _as_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError("Expected true/false.")


def _runtime_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd().resolve()


def _resolve_out_dir(out_value: str | None, command: str) -> Path:
    if out_value:
        out_dir = Path(out_value).resolve()
        ensure_dir(out_dir)
        return out_dir

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    out_dir = _runtime_base_dir() / "runs" / f"{command}_{stamp}"
    ensure_dir(out_dir)
    print(f"Auto output directory: {out_dir}")
    return out_dir


def _annotate_pdf(args: argparse.Namespace) -> None:
    pages = parse_pages_and_visuals(args.input)
    include_types = parse_type_filters(args.include_types)
    exclude_types = parse_type_filters(args.exclude_types)
    if not include_types and not exclude_types:
        exclude_types = set(DEFAULT_EXCLUDED_TYPES)

    filtered_pages = build_numbered_pages(
        pages,
        numbering_scope=args.numbering_scope,
        include_types=include_types,
        exclude_types=exclude_types,
    )
    export_inventory(filtered_pages, args.out)
    stats = annotate_pdf(
        pages=filtered_pages,
        pdf_path=args.pdf,
        out_root=args.out,
        dpi=args.dpi,
        bg_mode=args.bg_mode,
        draw_box=args.draw_box,
        label_position=args.label_position,
        pageid_position=args.pageid_position,
    )
    print(
        "PDF annotation complete."
        f" pdf_pages={stats['pdf_pages']}, pbir_pages={stats['pbir_pages']},"
        f" annotated_pages={stats['annotated_pages']}, annotated_visuals={stats['annotated_visuals']}"
    )


def _run_all(args: argparse.Namespace) -> None:
    _annotate_pdf(args)
    _build(args.input, args.out, write_inventory=False)
    _validate(args.input, args.out)
    print("Run-all complete.")


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pbir-mock", description="PBIR mock inventory and viewer generator.")
    subparsers = parser.add_subparsers(dest="command", required=False)

    build_cmd = subparsers.add_parser("build", help="Generate inventory CSVs and HTML mock viewer.")
    build_cmd.add_argument("input", nargs="?", default="definition", help="Path to PBIR definition folder.")
    build_cmd.add_argument("--out", default=None, help="Output folder path. If omitted, auto-creates run folder.")

    validate_cmd = subparsers.add_parser("validate", help="Run validations and write CSV reports.")
    validate_cmd.add_argument("input", nargs="?", default="definition", help="Path to PBIR definition folder.")
    validate_cmd.add_argument("--out", default=None, help="Output folder path. If omitted, auto-creates run folder.")

    annotate_cmd = subparsers.add_parser("annotate-pdf", help="Annotate exported PDF pages with PBIR page and visual numbers.")
    annotate_cmd.add_argument("--input", default="definition", help="Path to PBIR definition folder.")
    annotate_cmd.add_argument("--pdf", required=True, help="Path to exported report PDF file.")
    annotate_cmd.add_argument("--out", default=None, help="Output folder path. If omitted, auto-creates run folder.")
    annotate_cmd.add_argument("--bg-mode", choices=["by_order", "by_pageid", "by_name"], default="by_order")
    annotate_cmd.add_argument("--numbering-scope", choices=["page", "report"], default="page")
    annotate_cmd.add_argument("--include-types", action="append", help="Visual types to include (comma-separated or repeated).")
    annotate_cmd.add_argument("--exclude-types", action="append", help="Visual types to exclude (comma-separated or repeated).")
    annotate_cmd.add_argument("--dpi", type=int, default=200, help="Render DPI for PDF pages.")
    annotate_cmd.add_argument("--draw-box", type=_as_bool, default=True, help="Draw bounding boxes around visuals.")
    annotate_cmd.add_argument("--label-position", choices=["top-left", "top-right", "center"], default="top-left")
    annotate_cmd.add_argument("--pageid-position", choices=["top-left", "top-right"], default="top-left")

    run_all_cmd = subparsers.add_parser("run-all", help="Run annotate-pdf, build mock viewer, and validate in one command.")
    run_all_cmd.add_argument("--input", default="definition", help="Path to PBIR definition folder.")
    run_all_cmd.add_argument("--pdf", required=True, help="Path to exported report PDF file.")
    run_all_cmd.add_argument("--out", default=None, help="Output folder path. If omitted, auto-creates run folder.")
    run_all_cmd.add_argument("--bg-mode", choices=["by_order", "by_pageid", "by_name"], default="by_order")
    run_all_cmd.add_argument("--numbering-scope", choices=["page", "report"], default="page")
    run_all_cmd.add_argument("--include-types", action="append", help="Visual types to include (comma-separated or repeated).")
    run_all_cmd.add_argument("--exclude-types", action="append", help="Visual types to exclude (comma-separated or repeated).")
    run_all_cmd.add_argument("--dpi", type=int, default=200, help="Render DPI for PDF pages.")
    run_all_cmd.add_argument("--draw-box", type=_as_bool, default=True, help="Draw bounding boxes around visuals.")
    run_all_cmd.add_argument("--label-position", choices=["top-left", "top-right", "center"], default="top-left")
    run_all_cmd.add_argument("--pageid-position", choices=["top-left", "top-right"], default="top-left")

    return parser


def main() -> None:
    parser = make_parser()
    args = parser.parse_args()

    command = args.command or "build"
    if command == "build":
        input_dir = Path(args.input).resolve()
        out_dir = _resolve_out_dir(args.out, "build")
        if not input_dir.exists():
            raise SystemExit(f"Input directory not found: {input_dir}")
        _build(input_dir, out_dir)
        return
    if command == "validate":
        input_dir = Path(args.input).resolve()
        out_dir = _resolve_out_dir(args.out, "validate")
        if not input_dir.exists():
            raise SystemExit(f"Input directory not found: {input_dir}")
        _validate(input_dir, out_dir)
        return
    if command == "annotate-pdf":
        args.input = Path(args.input).resolve()
        args.pdf = Path(args.pdf).resolve()
        args.out = _resolve_out_dir(args.out, "annotate_pdf")
        if not args.input.exists():
            raise SystemExit(f"Input directory not found: {args.input}")
        if not args.pdf.exists():
            raise SystemExit(f"PDF file not found: {args.pdf}")
        _annotate_pdf(args)
        return
    if command == "run-all":
        args.input = Path(args.input).resolve()
        args.pdf = Path(args.pdf).resolve()
        args.out = _resolve_out_dir(args.out, "run_all")
        if not args.input.exists():
            raise SystemExit(f"Input directory not found: {args.input}")
        if not args.pdf.exists():
            raise SystemExit(f"PDF file not found: {args.pdf}")
        _run_all(args)
        return

    raise SystemExit(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
