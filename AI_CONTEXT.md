# AI Context: `visualmap` / `pbir-mock` (v2)

## System Purpose
`pbir-mock` converts a PBIR `definition` folder into QA-ready artifacts:
- inventory CSVs
- HTML mock viewer with interaction wiring
- annotated PDF overlays
- validation CSV reports

It is designed for rapid QA/UAT checks when full Power BI runtime behavior is not available.

## High-Level Architecture
Pipeline components:
1. Discovery and parsing
2. Numbering and filtering
3. Exporters (inventory, viewer, pdf annotation, validation)
4. CLI orchestration (`build`, `annotate-pdf`, `validate`, `run-all`)
5. Optional EXE packaging with PyInstaller

## Core Domain Model
File: `pbir_mock/models.py`

- `Page`
  - `page_id`, `page_name`, `width`, `height`, `visuals`
- `Visual`
  - geometry: `x`, `y`, `width`, `height`, `z`
  - identity: `visual_id`, `visual_type`, `title`, `seq`, `label`
  - action wiring: `link_type`, `navigation_section`, `bookmark_target`, `web_url`
  - navigator metadata:
    - `navigator_rows`
    - `navigator_columns`
    - `navigator_orientation`
    - `navigator_target_ids`
- `Bookmark`
  - bookmark id/name, active section, visual container ids

## Parsing Layer
### Report parser
File: `pbir_mock/parsers/report_parser.py`
- Reads page and visual JSON files.
- Extracts standard visual metadata.
- Extracts action link metadata from `visualContainerObjects.visualLink`.
- Extracts `pageNavigator` layout:
  - `rowCount`, `columnCount`, `orientation`
- Extracts explicit navigator targets from `visual.objects.pages[*].selector`.

### Bookmark parser
File: `pbir_mock/parsers/bookmark_parser.py`
- Reads bookmark JSON files.
- Captures active section and section visual IDs.

### Navigation parser
File: `pbir_mock/parsers/navigation_parser.py`
- Parses button-level link wiring for validation rules.

## Numbering and Filtering
File: `pbir_mock/numbering.py`
- Centralized numbering to keep CSV and PDF consistent.
- Supports include/exclude type filters.
- Numbering scopes:
  - `page`
  - `report`
- Default exclusions include `textbox`, `basicShape`, `image`.

## Exporters
### Inventory exporter
File: `pbir_mock/exporters/inventory.py`
- Writes:
  - `inventory/pages.csv`
  - `inventory/visuals.csv`
  - `inventory/page_<safe>.csv`

### Mock viewer exporter
File: `pbir_mock/exporters/mock_viewer.py`

Generates:
- `mock/index.html`
- `mock/app.js`
- `mock/styles.css`
- `mock/report.json`

v2 interaction design:
- Page navigator no longer uses heuristic per-tab hotspot DIVs.
- Viewer renders one overlay box for navigator visual.
- Click-to-target mapping inside navigator uses deterministic math:
  - relative click (`rx`, `ry`) in navigator box
  - row/col from configured `rowCount`/`columnCount`
  - index -> target page list
- Target list source:
  - navigator explicit targets when available
  - fallback to PBIR page order

v2 scaling:
- `fit` uses viewport width and height.
- scale is capped at `1` unless explicit zoom is selected.

v2 calibration:
- Each page gets per-page content bounds from PDF-rendered background.
- Global median margins are computed across pages.
- Default mapping uses global median bounds.
- Per-page bounds are used only for outliers (`>15px` margin delta).

v2 debug mode:
- UI toggle `Nav Debug`.
- Shows navigator bounding box and row/col grid.
- Logs click diagnostics (`row`, `col`, `idx`) in browser console.

### PDF annotator exporter
File: `pbir_mock/exporters/pdf_annotator.py`
- Renders PDF pages to PNG.
- Draws page id and visual sequence labels.
- Writes annotated PNGs and merged PDF.
- Writes PDF page mapping CSV.

### Validation exporter
File: `pbir_mock/exporters/validation.py`
- Writes all validation output CSVs.

## Validation Engine
File: `pbir_mock/validate.py`
- Off-canvas visuals
- Overlaps
- Bookmark reference integrity
- Navigation target checks
- Click-block risk where a higher-z visual overlaps action button area

## CLI Orchestration
File: `pbir_mock/cli.py`
- `build`
- `annotate-pdf`
- `validate`
- `run-all` (`annotate-pdf -> build -> validate`)

Output directory behavior:
- explicit `--out` uses caller path
- no `--out` creates run folder:
  - source mode: `<cwd>/runs/<command>_<timestamp>`
  - EXE mode: `<exe_dir>/runs/<command>_<timestamp>`

## Packaging
File: `build_exe.ps1`
- PyInstaller one-file build
- output: `dist/pbir-mock.exe`

## Dependencies
- `pymupdf` (`fitz`) for PDF rendering
- `pillow` for image drawing and bounds detection

## Known Design Decisions
- Viewer is intentionally static and deterministic; no full Power BI semantics.
- `pageNavigator` behavior prioritizes stable click mapping over stylistic visual fidelity.
- Navigator click mapping is based on PBIR row/column metadata and page order, not OCR/text extraction.
