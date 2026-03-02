# visualmap (`pbir-mock`)

`pbir-mock` is a Python CLI for Power BI PBIR folders. It can:
- parse pages/visuals
- export inventory CSVs
- generate an HTML mock viewer
- annotate exported report PDFs with visual numbers
- run validation checks (layout, bookmarks, navigation, click-block risks)

## Project Structure
- `pbir_mock/` core package modules
- `pbir-mock.py` CLI entry script
- `build_exe.ps1` one-step Windows EXE build script
- `pyproject.toml` packaging metadata
- `AI_CONTEXT.md` project reference for future AI-assisted work
- `RELEASE_NOTES.md` versioned changes

## Requirements
- Python `3.9+` (tested on 3.12)
- Windows (for `build_exe.ps1` + EXE flow)

Install dependencies:

```powershell
python -m pip install -e .
```

## CLI Commands (Source)

```powershell
python pbir-mock.py build <definition_path> --out <out_path>
python pbir-mock.py validate <definition_path> --out <out_path>
python pbir-mock.py annotate-pdf --input <definition_path> --pdf <report.pdf> --out <out_path>
python pbir-mock.py run-all --input <definition_path> --pdf <report.pdf> --out <out_path>
```

`run-all` executes: `annotate-pdf` -> `build` -> `validate`.

If `--out` is omitted, a unique run folder is auto-created:
- Source run: `<current_working_dir>/runs/...`
- EXE run: `<exe_folder>/runs/...`

## Build EXE

From repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

Output:
- `dist\pbir-mock.exe`

## Run EXE (Important Directory Step)

Change to the folder where the EXE exists, then run:

```powershell
cd .\dist
.\pbir-mock.exe run-all --input "<path>\definition" --pdf "<path>\report.pdf"
```

If you do not provide `--out`, outputs are created automatically under:
- `.\runs\run_all_YYYYMMDD_HHMMSS_microseconds`

## Main Outputs
- `inventory/*.csv`
- `mock/index.html`, `mock/app.js`, `mock/styles.css`, `mock/report.json`
- `annotated/pages_raw/*.png`, `annotated/pages_annotated/*.png`, `annotated/report_annotated.pdf`
- `validation/*.csv`

