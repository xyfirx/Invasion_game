from __future__ import annotations

import json
from pathlib import Path


def load_save_data(save_path: Path) -> dict[str, dict[str, float | int]]:
    if not save_path.exists():
        return {}
    try:
        with save_path.open("r", encoding="utf-8") as save_file:
            raw = json.load(save_file)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return raw


def save_save_data(save_path: Path, best_results: dict[str, dict[str, float | int]]) -> None:
    try:
        with save_path.open("w", encoding="utf-8") as save_file:
            json.dump(best_results, save_file, ensure_ascii=False, indent=2)
    except OSError:
        pass
