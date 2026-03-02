# visualmap (`pbir-mock`)

`pbir-mock` is a PBIR analysis and mock-runner CLI for QA and report validation.

It does:
- PBIR parsing for pages, visuals, bookmarks, and navigator layout metadata
- inventory CSV export
- HTML mock viewer generation with clickable interactions
- annotated PDF generation with page/visual labels
- validation reports for structural and interaction risks

## Main Capabilities
- Parse:
  - `definition/report.json`
  - `definition/pages/pages.json`
  - `definition/pages/<PAGE_ID>/page.json`
  - `definition/pages/<PAGE_ID>/visuals/<VISUAL_ID>/visual.json`
  - `definition/bookmarks/*.bookmark.json`
- Export inventory:
  - `inventory/pages.csv`
  - `inventory/visuals.csv`
  - `inventory/page_<page_name_safe>.csv`
- HTML mock viewer:
  - sidebar page list + search
  - background image rendering from annotated PDF page exports
  - high-contrast visual numbering overlays
  - action wiring for `PageNavigation`, `Bookmark`, `Back`, `WebUrl`
  - pageNavigator robust single-overlay click mapping (`row/col` hit-test)
  - optional debug grid overlay for navigator verification
- PDF annotation:
  - page id marker + visual sequence markers
  - annotated PNG pages + merged annotated PDF
- Validation:
  - off-canvas
  - overlap
  - bookmark references
  - navigation wiring
  - click-block risk

## Project Structure
- `pbir_mock/` core package
- `pbir-mock.py` CLI entrypoint
- `build_exe.ps1` EXE build script
- `pyproject.toml` package metadata
- `AI_CONTEXT.md` architecture and implementation context
- `RELEASE_NOTES.md` version history
- `BUG_CYCLE_V2.md` design/bug cycle log for navigator stabilization

## Requirements
- Python `3.9+` (tested with 3.12)
- Windows for EXE workflow

Install:
```powershell
python -m pip install -e .
```

## Source Usage
```powershell
python pbir-mock.py build <definition_path> --out <out_path>
python pbir-mock.py validate <definition_path> --out <out_path>
python pbir-mock.py annotate-pdf --input <definition_path> --pdf <report.pdf> --out <out_path>
python pbir-mock.py run-all --input <definition_path> --pdf <report.pdf> --out <out_path>
```

`run-all` executes:
1. `annotate-pdf`
2. `build`
3. `validate`

If `--out` is omitted, run folders are auto-created:
- source mode: `<cwd>/runs/<command>_<timestamp>`
- EXE mode: `<exe_folder>/runs/<command>_<timestamp>`

## Build EXE
From repo root:
```powershell
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

EXE output:
- `dist\pbir-mock.exe`

## Run EXE (Important)
Always change directory to the folder that contains the EXE before running:
```powershell
cd D:\Projects\visualmap_repo\dist
.\pbir-mock.exe run-all --input "<path>\definition" --pdf "<path>\report.pdf"
```

Optional explicit output:
```powershell
.\pbir-mock.exe run-all --input "<path>\definition" --pdf "<path>\report.pdf" --out ".\out_my_run"
```

Without `--out`, generated output is created under:
- `.\runs\run_all_YYYYMMDD_HHMMSS_microseconds`

## Output Artifacts
- `inventory/*.csv`
- `mock/index.html`
- `mock/app.js`
- `mock/styles.css`
- `mock/report.json`
- `annotated/pages_raw/*.png`
- `annotated/pages_annotated/*.png`
- `annotated/report_annotated.pdf`
- `validation/*.csv`
