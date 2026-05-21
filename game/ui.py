from __future__ import annotations

import pygame

from .constants import (
    ACCENT,
    CELL_SIZE,
    DANGER,
    FIELD_HEIGHT,
    FIELD_WIDTH,
    GRID_COLS,
    GRID_ROWS,
    LEVELS,
    OBSTACLE_NAMES,
    SIDEBAR_WIDTH,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SUCCESS,
    TEXT,
    TOWER_DESCRIPTIONS,
    TOWER_TYPES,
)
from .entities import Tower
from .utils import star_text, theme_path_tint


def draw(game: "Game") -> None:
    pass
