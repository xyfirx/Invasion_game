from __future__ import annotations

from dataclasses import dataclass
import math

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
    slow_factor: float = 1.0
    slow_timer: float = 0.0

    @property
    def alive(self) -> bool:
        return self.hp > 0

    @property
    def path_progress(self) -> float:
        return self.waypoint_index + self.segment_progress

    def apply_slow(self, factor: float, duration: float) -> None:
        if duration <= 0:
            return
        self.slow_factor = min(self.slow_factor, factor)
        self.slow_timer = max(self.slow_timer, duration)

    def take_damage(self, amount: float) -> bool:
        self.hp -= amount
        return self.hp <= 0

    def update(self, dt: float, waypoints: list[tuple[float, float]]) -> bool:
        if self.slow_timer > 0:
            self.slow_timer -= dt
            if self.slow_timer <= 0:
                self.slow_factor = 1.0

        movement = self.speed * self.slow_factor * dt
        while movement > 0 and self.waypoint_index < len(waypoints) - 1:
            nx, ny = waypoints[self.waypoint_index + 1]
            dx = nx - self.x
            dy = ny - self.y
            dist = math.hypot(dx, dy)

            if dist <= movement:
                self.x = nx
                self.y = ny
                self.waypoint_index += 1
                self.segment_progress = 0.0
                movement -= dist
            else:
                if dist > 0:
                    ratio = movement / dist
                    self.x += dx * ratio
                    self.y += dy * ratio
                    self.segment_progress += ratio
                movement = 0

        return self.waypoint_index >= len(waypoints) - 1

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
        if self.target is None or not self.target.alive:
            return True

        dx = self.target.x - self.x
        dy = self.target.y - self.y
        dist = math.hypot(dx, dy)
        max_move = self.speed * dt

        if dist <= max_move + self.target.radius:
            self.x = self.target.x
            self.y = self.target.y
            return True

        if dist > 0:
            ratio = max_move / dist
            self.x += dx * ratio
            self.y += dy * ratio
        return False


def distance_sq(ax: float, ay: float, bx: float, by: float) -> float:
    dx = ax - bx
    dy = ay - by
    return dx * dx + dy * dy
