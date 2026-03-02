from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    import json

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sanitize_name(name: str) -> str:
    compact = re.sub(r"\s+", "_", name.strip())
    compact = re.sub(r"[^A-Za-z0-9_-]", "_", compact)
    compact = re.sub(r"_+", "_", compact).strip("_")
    return compact or "unnamed"


def strip_single_quotes(value: str) -> str:
    text = value.strip()
    if len(text) >= 2 and text[0] == "'" and text[-1] == "'":
        return text[1:-1]
    return text


def extract_literal_value(container: dict[str, Any], path: list[str]) -> str:
    current: Any = container
    for key in path:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)
    if isinstance(current, str):
        return strip_single_quotes(current)
    return ""


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def safe_page_csv_name(base: str, seen: set[str]) -> str:
    name = base
    idx = 2
    while name in seen:
        name = f"{base}_{idx}"
        idx += 1
    seen.add(name)
    return name

