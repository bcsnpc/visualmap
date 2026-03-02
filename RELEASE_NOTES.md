# Release Notes

## v1.0.0
Initial public version of `pbir-mock`.

### Added
- PBIR parsing for pages, visuals, and bookmarks
- Inventory exports:
  - `inventory/pages.csv`
  - `inventory/visuals.csv`
  - `inventory/page_<name>.csv`
- HTML mock viewer:
  - sidebar page search/list
  - exact visual overlay coordinates
  - filtered visual numbering overlays
  - page image background support from annotated PDF renders
  - action wiring for buttons:
    - `PageNavigation`
    - `Bookmark`
    - `Back`
    - `WebUrl`
- PDF annotation pipeline:
  - PBIR page order mapping to PDF pages
  - raw page render export
  - high-contrast page id + visual number labels
  - optional visual region box overlay
  - annotated page PNGs + merged annotated PDF
  - warnings for page count mismatch
- Validation reports:
  - off-canvas
  - overlap
  - bookmark reference integrity
  - navigation target integrity
  - click-block risk detection for action buttons
- Unified single-command flow:
  - `run-all` (annotate -> build -> validate)
- Auto output run-folder generation when `--out` is omitted
  - source mode: `<cwd>/runs/...`
  - EXE mode: `<exe_folder>/runs/...`

### Packaging
- Added Windows EXE build script (`build_exe.ps1`)
- PyInstaller one-file packaging support for `pbir-mock.exe`

