from __future__ import annotations

import math
import random

import pygame

from .constants import (
    CELL_SIZE,
    FIELD_HEIGHT,
    FIELD_WIDTH,
    GRID_COLS,
    GRID_ROWS,
    LEVELS,
    TOWER_TYPES,
)
from .entities import Enemy, Projectile, Tower
from .utils import distance_sq


def build_path_tiles(points: list[tuple[int, int]]) -> set[tuple[int, int]]:
    tiles: set[tuple[int, int]] = set()
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        dx = 0 if x1 == x2 else (1 if x2 > x1 else -1)
        dy = 0 if y1 == y2 else (1 if y2 > y1 else -1)

        x, y = x1, y1
        tiles.add((x, y))
        while (x, y) != (x2, y2):
            x += dx
            y += dy
            tiles.add((x, y))
    return tiles


def cell_center(col: int, row: int) -> tuple[float, float]:
    return col * CELL_SIZE + CELL_SIZE / 2, row * CELL_SIZE + CELL_SIZE / 2


def tile_for_pos(x: float, y: float) -> tuple[int, int]:
    return int(x // CELL_SIZE), int(y // CELL_SIZE)


def occupied_tiles(towers: list[Tower]) -> set[tuple[int, int]]:
    occupied: set[tuple[int, int]] = set()
    for tower in towers:
        occupied.add(tile_for_pos(tower.x, tower.y))
    return occupied


def build_obstacles(game: "Game") -> list[dict[str, object]]:
    obstacles: list[dict[str, object]] = []
    for obstacle_type, col, row in game.current_level.obstacles:
        obstacles.append(
            {
                "type": obstacle_type,
                "col": col,
                "row": row,
                "rect": pygame.Rect(col * CELL_SIZE + 6, row * CELL_SIZE + 6, CELL_SIZE - 12, CELL_SIZE - 12),
            }
        )
    return obstacles


def find_obstacle(obstacles: list[dict[str, object]], col: int, row: int) -> dict[str, object] | None:
    for obstacle in obstacles:
        if obstacle["col"] == col and obstacle["row"] == row:
            return obstacle
    return None


def target_angle(tower: Tower, enemy: Enemy) -> float:
    return math.atan2(enemy.y - tower.y, enemy.x - tower.x)


def choose_target(tower: Tower, enemies: list[Enemy]) -> Enemy | None:
    r2 = tower.stats.range_px * tower.stats.range_px
    best: Enemy | None = None
    best_progress = -1.0
    for enemy in enemies:
        if not enemy.alive:
            continue
        if distance_sq(tower.x, tower.y, enemy.x, enemy.y) > r2:
            continue
        if enemy.path_progress > best_progress:
            best = enemy
            best_progress = enemy.path_progress
    return best


def apply_hit(target: Enemy, stats: "TowerStats", damage: float, enemies: list[Enemy], register_enemy_kill: callable) -> None:
    if not target.alive:
        return

    died = target.take_damage(damage)
    if stats.slow_duration > 0:
        target.apply_slow(stats.slow_factor, stats.slow_duration)

    if stats.splash_radius > 0:
        sr2 = stats.splash_radius * stats.splash_radius
        for other in enemies:
            if other is target or not other.alive:
                continue
            if distance_sq(target.x, target.y, other.x, other.y) <= sr2:
                splash_kill = other.take_damage(damage * 0.55)
                if splash_kill:
                    register_enemy_kill(other)

    if died:
        register_enemy_kill(target)


def place_tower(game: "Game", mx: float, my: float) -> None:
    if game.selected_tower_type is None or game.game_over or game.victory:
        return
    if not (0 <= mx < FIELD_WIDTH and 0 <= my < FIELD_HEIGHT):
        return

    col = int(mx // CELL_SIZE)
    row = int(my // CELL_SIZE)
    tile = (col, row)

    if col < 0 or row < 0 or col >= GRID_COLS or row >= GRID_ROWS:
        return
    if tile in game.path_tiles:
        return
    if tile in occupied_tiles(game.towers):
        return
    if find_obstacle(game.obstacles, col, row) is not None:
        return

    stats = TOWER_TYPES[game.selected_tower_type]
    if game.money < stats.cost:
        return

    game.money -= stats.cost
    x, y = cell_center(col, row)
    game.towers.append(Tower(x=x, y=y, tower_type=game.selected_tower_type, stats=stats))


def remove_obstacle(game: "Game", obstacle: dict[str, object]) -> bool:
    cost = game.current_level.obstacle_cost
    if game.money < cost:
        return False

    game.money -= cost
    game.obstacles.remove(obstacle)
    return True


def register_enemy_kill(game: "Game", enemy: Enemy) -> None:
    game.money += enemy.reward
    game.total_kills += 1
    game.wave_kills += 1


def spawn_enemy(game: "Game") -> None:
    if not game.waypoints:
        return

    sx, sy = game.waypoints[0]

    hp = (88 + game.wave_number * 26 + random.randint(-12, 20)) * game.current_level.enemy_hp_mult
    speed = (52 + game.wave_number * 3.8) * game.current_level.enemy_speed_mult
    reward = 8 + game.wave_number // 2
    damage = 1
    radius = 16
    variant = "scout"
    color = (89, 224, 127)

    roll = random.random()
    if roll < 0.18 + game.wave_number * 0.012:
        hp *= 0.72
        speed *= 1.42
        reward += 1
        radius = 13
        variant = "scout"
        color = (123, 248, 178)
    elif roll > 0.86:
        hp *= 1.95
        speed *= 0.7
        reward += 6
        damage = 2
        radius = 20
        variant = "brute"
        color = (244, 143, 115)
    elif roll > 0.62:
        hp *= 1.15
        speed *= 1.12
        reward += 3
        radius = 15
        variant = "stalker"
        color = (148, 208, 255)

    game.enemies.append(
        Enemy(
            x=sx,
            y=sy,
            hp=hp,
            max_hp=hp,
            speed=speed,
            reward=reward,
            damage=damage,
            radius=radius,
            color=color,
            variant=variant,
        )
    )


def start_wave(game: "Game") -> None:
    if game.game_over or game.victory or game.in_wave:
        return

    game.wave_number += 1
    game.wave_spawned = 0
    game.wave_to_spawn = min(20, 5 + game.wave_number * 3)
    game.spawn_cooldown = 0.0
    game.wave_kills = 0
    game.in_wave = True

    if game.wave_number > game.current_level.waves:
        game.wave_number = game.current_level.waves
        game.in_wave = False
