# Release Notes

## v2.0.0
Navigator stability and viewer calibration release.

### Added
- Robust `pageNavigator` interaction model in HTML viewer:
  - single overlay per navigator visual
  - click hit-test via row/column math from PBIR layout
  - deterministic target resolution using explicit navigator targets or PBIR page order
- Viewer debug mode:
  - `Nav Debug` toggle
  - navigator bounding box + row/column grid lines
  - click diagnostics in browser console
- Calibration strategy upgrade:
  - global median content-bounds mapping across pages
  - automatic per-page outlier fallback (`>15px` margin deviation)
- Fit-to-viewport scaling:
  - uses both available width and height
  - capped at 100% unless manual zoom selected
- Parser support for navigator target metadata:
  - `navigator_target_ids` on `Visual`

### Changed
- Removed heuristic per-tab hotspot generation for `pageNavigator` (root cause of drift/splitting).
- `mock/report.json` now carries:
  - `pageOrderIds`
  - `contentBoundsMode`
  - navigator metadata fields for deterministic runtime click mapping

### Fixed
- Page navigator drift across pages with different background margins.
- Split/floating navigator hotspots on compact navigator bars.
- Inconsistent click areas across multi-row navigators.
- Fit mode requiring frequent browser zoom adjustment on large pages.

### Packaging
- Rebuilt `dist/pbir-mock.exe` for v2 with no `build_exe.ps1` changes required.

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
