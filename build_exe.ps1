$ErrorActionPreference = "Stop"

python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --name pbir-mock `
  --collect-all fitz `
  --collect-all PIL `
  pbir-mock.py

Write-Host "Executable created at: dist\\pbir-mock.exe"

