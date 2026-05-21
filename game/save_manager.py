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

    results: dict[str, dict[str, float | int]] = {}
    for key, value in raw.items():
        if isinstance(value, dict):
            results[key] = {
                "best_stars": int(value.get("best_stars", 0)),
                "best_score": float(value.get("best_score", 10**9)),
                "best_time": float(value.get("best_time", 0.0)),
                "best_damage": int(value.get("best_damage", 0)),
            }
    return results


def save_save_data(save_path: Path, best_results: dict[str, dict[str, float | int]]) -> None:
    try:
        with save_path.open("w", encoding="utf-8") as save_file:
            json.dump(best_results, save_file, ensure_ascii=False, indent=2)
    except OSError:
        pass
