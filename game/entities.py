from dataclasses import dataclass

@dataclass
class Enemy:
    x: float
    y: float
    hp: float
    max_hp: float
    speed: float
    reward: int
    damage: int
    radius: float
    color: tuple[int, int, int]
    variant: str = "scout"
    waypoint_index: int = 0
    segment_progress: float = 0.0

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def update(self, dt: float, waypoints: list[tuple[float, float]]) -> bool:
        return False

@dataclass
class Tower:
    x: float
    y: float
    tower_type: str
    stats: "TowerStats"
    cooldown: float = 0.0
    aim_angle: float = -1.5707963267948966
    recoil_timer: float = 0.0

    def update(self, dt: float) -> None:
        self.cooldown = max(0.0, self.cooldown - dt)
        self.recoil_timer = max(0.0, self.recoil_timer - dt)

@dataclass
class Projectile:
    x: float
    y: float
    target: Enemy | None
    stats: "TowerStats"
    damage: float
    speed: float
    color: tuple[int, int, int]

    def update(self, dt: float) -> bool:
        return True


def distance_sq(ax: float, ay: float, bx: float, by: float) -> float:
    dx = ax - bx
    dy = ay - by
    return dx * dx + dy * dy
