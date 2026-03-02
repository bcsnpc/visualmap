# AI Context: `visualmap` / `pbir-mock`

## Purpose
`pbir-mock` turns a PBIR `definition` folder into:
- inventory CSVs
- HTML page mock with visual overlays and action wiring
- annotated PDF exports with sequence numbers
- validation reports for structure and interaction risks

## Core Data Model
File: `pbir_mock/models.py`
- `Page`: page metadata + visuals
- `Visual`: layout, type, title, seq, action link metadata
- `Bookmark`: bookmark id/name + active section + section visual ids

## Parsing
- `pbir_mock/parsers/report_parser.py`
  - reads `pages/page.json` and `visuals/*/visual.json`
  - extracts:
    - page display name/width/height
    - visual id/type/position/z/title
    - action link fields (`type`, `navigationSection`, `bookmark`, `webUrl`)
- `pbir_mock/parsers/bookmark_parser.py`
  - reads `bookmarks/*.bookmark.json`
  - extracts active section and section visual container ids
- `pbir_mock/parsers/navigation_parser.py`
  - parses action-button navigation details for validation

## Numbering/Filtering Logic
File: `pbir_mock/numbering.py`
- Shared filtering + numbering logic for consistency across CSV and PDF
- Default excluded visual types:
  - `textbox`, `basicShape`, `image`
- Numbering scopes:
  - `page` (restart each page)
  - `report` (global running index)

## Exporters
- `pbir_mock/exporters/inventory.py`
  - writes `pages.csv`, `visuals.csv`, and per-page CSVs
- `pbir_mock/exporters/mock_viewer.py`
  - outputs static mock app (`index.html`, `app.js`, `styles.css`, `report.json`)
  - supports:
    - background page images (`out/annotated/pages_raw/page_###.png`)
    - filtered visual-number overlays
    - action-button behavior:
      - page navigation
      - bookmark navigation/context
      - back
      - web URL
- `pbir_mock/exporters/pdf_annotator.py`
  - renders PDF pages to images (PyMuPDF)
  - overlays page ids + visual sequence numbers (Pillow)
  - emits annotated images + merged annotated PDF + page map CSV
- `pbir_mock/exporters/validation.py`
  - writes all validation CSV reports

## Validation
File: `pbir_mock/validate.py`
- Off-canvas visuals
- Overlapping visuals
- Bookmark reference checks
- Navigation target checks (`PageNavigation`, `Bookmark`, `WebUrl`)
- Click-block risk:
  - action button overlapped by higher-`z` visuals

## CLI
File: `pbir_mock/cli.py`
- `build`
- `validate`
- `annotate-pdf`
- `run-all` (annotate -> build -> validate)

### Output Directory Behavior
- If `--out` is provided, use it.
- If omitted:
  - Source: create under `<cwd>/runs/<command>_<timestamp>`
  - EXE: create under `<exe_dir>/runs/<command>_<timestamp>`

## EXE Packaging
- Script: `build_exe.ps1`
- Tool: PyInstaller (`--onefile`)
- Output: `dist/pbir-mock.exe`

## Key Dependencies
- `pymupdf` (imported as `fitz`) for PDF rendering
- `pillow` for image annotation

## Common Workflow
1. `annotate-pdf` to create page backgrounds and annotated PDF
2. `build` to generate inventory + mock viewer
3. `validate` for integrity/risk reports
4. Or use `run-all` for one-command execution

