# Bug Cycle Log: Navigator Stabilization (v2)

## Scope
This document captures the design and bug-fix cycle for stabilizing HTML mock viewer navigation alignment, especially `pageNavigator` visuals on PDF background images.

## Initial Problem
Observed QA issues:
1. Page navigator click zones drifted from visual tabs.
2. Multi-row navigators produced large overlapping click strips.
3. Compact navigators produced split/floating hotspot fragments.
4. Fit mode often required manual browser zoom adjustment.

## Iteration History
### Cycle 1: Heuristic hotspot generation
- Approach:
  - generated multiple hotspot DIVs per navigator tab
  - used row/column metadata plus image border heuristics
- Result:
  - partial improvements on some pages
  - unstable across pages with different margins and navigator densities

### Cycle 2: Image-analysis tuning
- Added:
  - horizontal and vertical border detection
  - largest-segment selection
  - compact navigator fallback heuristics
- Result:
  - still inconsistent
  - could not guarantee cross-page stability

### Cycle 3: Root-cause correction
- Found:
  - path/base-resolution issues causing unintended fallback behavior
  - per-page calibration variance amplified visual drift
- Result:
  - better but still not robust enough

## Final v2 Resolution
### Decision
Stop generating per-tab hotspot DIVs.

### Implementation
1. Single overlay for each `pageNavigator` visual.
2. Runtime click hit-testing inside overlay:
   - compute normalized click (`rx`, `ry`)
   - derive `row`, `col`, then `idx`
   - navigate using target list (explicit targets or PBIR page order fallback)
3. Fit scaling uses both width and height (viewport-aware).
4. Calibration defaults to global median content bounds.
5. Outlier pages use per-page bounds only when margins deviate by more than 15px.
6. Debug mode added for verification:
   - navigator box
   - row/column grid
   - click logs in console

## Why This Works Better
- Removes geometry overfitting and heuristic hotspot fragmentation.
- Uses deterministic PBIR layout metadata for tab index mapping.
- Reduces per-page calibration noise by using global median bounds.
- Preserves diagnosability with explicit debug overlay and click logs.

## Validation Checklist Used
1. Home page large 3-row navigator:
   - click in each row maps to expected page index.
2. Compact navigators on other pages:
   - no split or floating hotspots.
3. Fit mode:
   - page visible without forced browser zoom changes.
4. Action buttons/bookmarks:
   - existing behaviors unchanged.

## Residual Risks
- If a report uses custom navigator visuals with non-grid semantics, row/column index mapping may not represent intended grouping.
- If PBIR navigator target metadata is sparse, fallback to page order may differ from hidden report logic.

## Future Enhancements
1. Add optional per-report navigator mapping overrides (`yaml/json` config).
2. Add browser-side telemetry export for click-to-target verification.
3. Add integration snapshot tests for representative navigator layouts.
