from dataclasses import dataclass

CELL_SIZE = 56
GRID_COLS = 16
GRID_ROWS = 12
FIELD_WIDTH = GRID_COLS * CELL_SIZE
FIELD_HEIGHT = GRID_ROWS * CELL_SIZE
SIDEBAR_WIDTH = 320
SCREEN_WIDTH = FIELD_WIDTH + SIDEBAR_WIDTH
SCREEN_HEIGHT = FIELD_HEIGHT
FPS = 60

BG_TOP = (16, 19, 34)
BG_BOTTOM = (38, 43, 68)
TEXT = (236, 240, 245)
ACCENT = (255, 191, 75)
DANGER = (255, 95, 109)
SUCCESS = (106, 214, 133)
PATH_COLOR = (122, 116, 88)
FIELD_GRID = (255, 255, 255, 18)

@dataclass(frozen=True)
class TowerStats:
    name: str
    cost: int
    damage: float
    range_px: float
    fire_rate: float
    projectile_speed: float
    color: tuple[int, int, int]
    slow_factor: float = 1.0
    slow_duration: float = 0.0
    splash_radius: float = 0.0

@dataclass(frozen=True)
class LevelStats:
    name: str
    path_cells: tuple[tuple[int, int], ...]
    waves: int
    start_money: int
    start_lives: int
    enemy_hp_mult: float
    enemy_speed_mult: float
    par_time: float
    base_score_time: float
    theme: str
    decor: tuple[str, ...]
    goal: str
    obstacle_cost: int
    obstacles: tuple[tuple[str, int, int], ...]

LEVELS: tuple[LevelStats, ...] = ()
TOWER_DESCRIPTIONS: dict[str, str] = {}
OBSTACLE_NAMES: dict[str, str] = {}
TOWER_TYPES: dict[str, TowerStats] = {}
