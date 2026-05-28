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

LEVELS: tuple[LevelStats, ...] = (
    LevelStats(
        name="Космическая битва",
        path_cells=(
            (0, 2), (2, 2), (2, 7), (5, 7), (5, 3),
            (9, 3), (9, 8), (13, 8), (13, 5), (15, 5),
        ),
        waves=5,
        start_money=220,
        start_lives=20,
        enemy_hp_mult=1.0,
        enemy_speed_mult=1.0,
        par_time=140.0,
        base_score_time=120.0,
        theme="desert",
        decor=("dune", "rock", "crater", "antenna"),
        goal="База людей",
        obstacle_cost=22,
        obstacles=(
            ("rock", 4, 5),
            ("rock", 7, 6),
            ("scrap", 11, 4),
            ("scrap", 9, 10),
        ),
    ),
    LevelStats(
        name="Стычка в поле",
        path_cells=(
            (0, 9), (2, 9), (2, 4), (5, 4), (5, 10), (8, 10),
            (8, 2), (11, 2), (11, 8), (14, 8), (14, 3), (15, 3),
        ),
        waves=6,
        start_money=250,
        start_lives=18,
        enemy_hp_mult=1.18,
        enemy_speed_mult=1.12,
        par_time=165.0,
        base_score_time=145.0,
        theme="field",
        decor=("tree", "hill", "barn", "windmill"),
        goal="Домик в деревне",
        obstacle_cost=28,
        obstacles=(
            ("tree", 3, 5),
            ("tree", 6, 3),
            ("hay", 9, 6),
            ("fence", 12, 7),
            ("rock", 7, 8),
        ),
    ),
    LevelStats(
        name="Нападение на город",
        path_cells=(
            (0, 6), (3, 6), (3, 2), (6, 2), (6, 9),
            (9, 9), (9, 3), (12, 3), (12, 8), (15, 8),
        ),
        waves=7,
        start_money=280,
        start_lives=16,
        enemy_hp_mult=1.35,
        enemy_speed_mult=1.22,
        par_time=200.0,
        base_score_time=175.0,
        theme="city",
        decor=("building", "tree", "streetlight", "car"),
        goal="Администрация города",
        obstacle_cost=35,
        obstacles=(
            ("building", 4, 4),
            ("car", 7, 5),
            ("tree", 10, 6),
            ("building", 11, 10),
            ("streetlight", 8, 7),
        ),
    ),
)

TOWER_DESCRIPTIONS: dict[str, str] = {
    "blaster": "Простая мощная пушка для стабильного урона по одним целям.",
    "frost": "Замедляет противников и удерживает их в зоне поражения дольше.",
    "pulse": "Снайперская пушка: медленно стреляет, но бьёт очень тяжело и далеко.",
}

OBSTACLE_NAMES: dict[str, str] = {
    "rock": "Камень",
    "tree": "Дерево",
    "scrap": "Обломки",
    "hay": "Стог сена",
    "fence": "Забор",
    "building": "Здание",
    "car": "Машина",
    "streetlight": "Фонарь",
}

TOWER_TYPES: dict[str, TowerStats] = {
    "blaster": TowerStats(
        name="Пушка",
        cost=70,
        damage=24,
        range_px=145,
        fire_rate=1.3,
        projectile_speed=330,
        color=(96, 204, 252),
    ),
    "frost": TowerStats(
        name="Замедлялка",
        cost=95,
        damage=12,
        range_px=130,
        fire_rate=0.9,
        projectile_speed=280,
        color=(161, 201, 255),
        slow_factor=0.58,
        slow_duration=1.8,
    ),
    "pulse": TowerStats(
        name="Снайпер",
        cost=150,
        damage=72,
        range_px=320,
        fire_rate=0.35,
        projectile_speed=420,
        color=(255, 148, 93),
    ),
}
