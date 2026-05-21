from __future__ import annotations

import math
from typing import cast

from .constants import LevelStats


def distance_sq(ax: float, ay: float, bx: float, by: float) -> float:
    dx = ax - bx
    dy = ay - by
    return dx * dx + dy * dy


def formatted_time(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    minutes, remaining = divmod(seconds, 60)
    return f"{minutes:02d}:{remaining:02d}"


def result_score(time_taken: float, damage_taken: int) -> float:
    return time_taken + damage_taken * 7.5


def star_for_result(level: LevelStats, time_taken: float, damage_taken: int, success: bool) -> int:
    if not success:
        return 0

    time_ratio = time_taken / max(1.0, level.par_time)
    damage_ratio = damage_taken / max(1, level.start_lives)
    quality = (1.0 / max(0.7, time_ratio)) * 0.65 + (1.0 - min(1.0, damage_ratio)) * 0.35

    if quality >= 0.92:
        return 3
    if quality >= 0.72:
        return 2
    return 1
