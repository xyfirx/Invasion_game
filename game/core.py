from __future__ import annotations

import json
import math
import random
import sys
import textwrap
from pathlib import Path
from typing import cast

import pygame

from .constants import (
    ACCENT,
    CELL_SIZE,
    DANGER,
    FIELD_HEIGHT,
    FIELD_WIDTH,
    FPS,
    GRID_COLS,
    GRID_ROWS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SIDEBAR_WIDTH,
    SUCCESS,
    TEXT,
    LEVELS,
    OBSTACLE_NAMES,
    TOWER_DESCRIPTIONS,
    TOWER_TYPES,
    LevelStats,
    TowerStats,
)
from .entities import Enemy, Projectile, Tower, distance_sq


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Вторжение: Оборона")
        self.fullscreen = False
        self.display = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.display_size = self.display.get_size()
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 22)
        self.small_font = pygame.font.SysFont("consolas", 16)
        self.big_font = pygame.font.SysFont("consolas", 48, bold=True)
        self.save_path = Path(__file__).resolve().parents[1] / "save_data.json"
        self.best_results = self._load_save_data()

        self.current_level_index = 0
        self.current_level: LevelStats = LEVELS[self.current_level_index]
        self.path_cells: list[tuple[int, int]] = []
        self.path_tiles: set[tuple[int, int]] = set()
        self.waypoints: list[tuple[float, float]] = []
        self.obstacles: list[dict[str, object]] = []
        self.level_result_open = False
        self.level_result: dict[str, object] | None = None
        self.menu_open = True
        self.level_select_open = False
        self.menu_selected_level = 0
        self.info_modal_open = False
        self.info_modal_kind: str | None = None
        self.info_modal_value: str | None = None
        self.info_modal_obstacle: dict[str, object] | None = None
        self.info_modal_rect: pygame.Rect | None = None
        self.info_modal_close_rect: pygame.Rect | None = None
        self.info_modal_action_rect: pygame.Rect | None = None
        self.menu_close_rect: pygame.Rect | None = None
        self.settings_close_rect: pygame.Rect | None = None
        self.level_select_close_rect: pygame.Rect | None = None
        self.level_result_close_rect: pygame.Rect | None = None
        self.menu_button_rect = pygame.Rect(14, 14, 112, 34)

        self.stars = []
        for _ in range(95):
            self.stars.append(
                [
                    random.uniform(0, FIELD_WIDTH),
                    random.uniform(0, FIELD_HEIGHT),
                    random.uniform(12, 38),
                    random.uniform(1.0, 2.7),
                ]
            )

        self.buttons: list[dict] = []
        self.menu_buttons: dict[str, pygame.Rect] = {}
        self.level_select_buttons: dict[str, pygame.Rect] = {}
        self._create_ui_buttons()

        self.reset_round(0)

    def _load_save_data(self) -> dict[str, dict[str, float | int]]:
        if not self.save_path.exists():
            return {}

        try:
            with self.save_path.open("r", encoding="utf-8") as save_file:
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

    def _save_save_data(self) -> None:
        try:
            with self.save_path.open("w", encoding="utf-8") as save_file:
                json.dump(self.best_results, save_file, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def reset_round(self, level_index: int | None = None) -> None:
        if level_index is not None:
            self.current_level_index = max(0, min(level_index, len(LEVELS) - 1))

        self.current_level = LEVELS[self.current_level_index]
        self.path_cells = list(self.current_level.path_cells)
        self.path_tiles = self._build_path_tiles(self.path_cells)
        self.waypoints = [self._cell_center(c, r) for c, r in self.path_cells]
        self.obstacles = self._build_obstacles()

        self.money = self.current_level.start_money
        self.lives = self.current_level.start_lives
        self.starting_lives = self.current_level.start_lives
        self.wave_number = 0
        self.in_wave = False
        self.wave_spawned = 0
        self.wave_kills = 0
        self.wave_to_spawn = 0
        self.spawn_cooldown = 0.0
        self.spawn_interval = 0.7
        self.towers: list[Tower] = []
        self.enemies: list[Enemy] = []
        self.projectiles: list[Projectile] = []
        self.selected_tower_type: str | None = "blaster"
        self.game_over = False
        self.victory = False
        self.settings_open = False
        self.level_result_open = False
        self.level_result = None
        self.level_result_buttons: dict[str, pygame.Rect] = {}
        self.total_kills = 0
        self.damage_taken = 0
        self.elapsed_time = 0.0
        self.level_best = self.best_results.get(str(self.current_level_index), {})
        self.info_modal_open = False
        self.info_modal_kind = None
        self.info_modal_value = None
        self.info_modal_obstacle = None
        self.info_modal_rect = None
        self.info_modal_close_rect = None
        self.info_modal_action_rect = None

    def _build_obstacles(self) -> list[dict[str, object]]:
        obstacles: list[dict[str, object]] = []
        for obstacle_type, col, row in self.current_level.obstacles:
            obstacles.append(
                {
                    "type": obstacle_type,
                    "col": col,
                    "row": row,
                    "rect": pygame.Rect(col * CELL_SIZE + 6, row * CELL_SIZE + 6, CELL_SIZE - 12, CELL_SIZE - 12),
                }
            )
        return obstacles

    def _find_obstacle(self, col: int, row: int) -> dict[str, object] | None:
        for obstacle in self.obstacles:
            if obstacle["col"] == col and obstacle["row"] == row:
                return obstacle
        return None

    def _open_info_modal(
        self,
        kind: str,
        value: str,
        obstacle: dict[str, object] | None = None,
    ) -> None:
        self.info_modal_open = True
        self.info_modal_kind = kind
        self.info_modal_value = value
        self.info_modal_obstacle = obstacle

    def _close_info_modal(self) -> None:
        self.info_modal_open = False
        self.info_modal_kind = None
        self.info_modal_value = None
        self.info_modal_obstacle = None
        self.info_modal_rect = None
        self.info_modal_close_rect = None
        self.info_modal_action_rect = None

    def start_game(self, level_index: int | None = None) -> None:
        self.menu_open = False
        self.level_select_open = False
        self.settings_open = False
        self.level_result_open = False
        if level_index is None:
            level_index = self.menu_selected_level
        self.reset_round(level_index)

    def open_menu(self) -> None:
        self.menu_open = True
        self.level_select_open = False
        self.settings_open = False
        self.level_result_open = False

    def _create_ui_buttons(self) -> None:
        x = FIELD_WIDTH + 20
        y = 260
        w = SIDEBAR_WIDTH - 40
        h = 56
        gap = 14

        self.buttons = []
        for tower_key in TOWER_TYPES:
            self.buttons.append(
                {
                    "kind": "tower",
                    "tower_key": tower_key,
                    "rect": pygame.Rect(x, y, w, h),
                }
            )
            y += h + gap

        self.buttons.append(
            {
                "kind": "wave",
                "rect": pygame.Rect(x, y + 20, w, 62),
            }
        )

        center_x = SCREEN_WIDTH // 2
        center_y = SCREEN_HEIGHT // 2
        self.settings_buttons = {
            "fullscreen": pygame.Rect(center_x - 230, center_y - 116, 460, 66),
            "back": pygame.Rect(center_x - 230, center_y + 176, 222, 54),
        }

        self.menu_close_rect = pygame.Rect(SCREEN_WIDTH - 52, 14, 34, 34)
        self.settings_close_rect = pygame.Rect(SCREEN_WIDTH - 52, 14, 34, 34)
        self.level_select_close_rect = pygame.Rect(SCREEN_WIDTH - 52, 14, 34, 34)
        self.level_result_close_rect = pygame.Rect(SCREEN_WIDTH - 52, 14, 34, 34)

        menu_center_x = SCREEN_WIDTH // 2
        menu_center_y = SCREEN_HEIGHT // 2
        self.menu_buttons = {
            "start": pygame.Rect(menu_center_x - 180, menu_center_y - 72, 360, 60),
            "levels": pygame.Rect(menu_center_x - 180, menu_center_y + 4, 360, 60),
            "settings": pygame.Rect(menu_center_x - 180, menu_center_y + 80, 360, 60),
            "exit": pygame.Rect(menu_center_x - 180, menu_center_y + 156, 360, 60),
        }

        self.level_select_buttons = {
            "level_0": pygame.Rect(menu_center_x - 230, menu_center_y - 40, 460, 64),
            "level_1": pygame.Rect(menu_center_x - 230, menu_center_y + 40, 460, 64),
            "level_2": pygame.Rect(menu_center_x - 230, menu_center_y + 120, 460, 64),
            "back": pygame.Rect(menu_center_x - 230, menu_center_y + 210, 220, 56),
            "start": pygame.Rect(menu_center_x + 10, menu_center_y + 210, 220, 56),
        }

    def _toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            desktop_width, desktop_height = pygame.display.get_desktop_sizes()[0]
            self.display = pygame.display.set_mode(
                (desktop_width, desktop_height),
                pygame.FULLSCREEN,
            )
        else:
            self.display = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

        self.display_size = self.display.get_size()

    def _formatted_time(self, seconds: float) -> str:
        seconds = max(0, int(round(seconds)))
        minutes, remaining = divmod(seconds, 60)
        return f"{minutes:02d}:{remaining:02d}"

    def _star_for_result(self, level: LevelStats, time_taken: float, damage_taken: int, success: bool) -> int:
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

    def _result_score(self, time_taken: float, damage_taken: int) -> float:
        return time_taken + damage_taken * 7.5

    def _update_best_result(self, level_index: int, result: dict[str, object]) -> None:
        key = str(level_index)
        current = self.best_results.get(key)
        new_score = cast(float, result["score"])

        if current is None or new_score < float(current.get("best_score", 10**9)):
            self.best_results[key] = {
                "best_stars": cast(int, result["stars"]),
                "best_score": new_score,
                "best_time": cast(float, result["time"]),
                "best_damage": cast(int, result["damage"]),
            }
            self._save_save_data()
        else:
            best_stars = int(current.get("best_stars", 0))
            if cast(int, result["stars"]) > best_stars:
                current["best_stars"] = cast(int, result["stars"])
                self._save_save_data()

    def _trigger_level_result(self, success: bool) -> None:
        stars = self._star_for_result(
            self.current_level,
            self.elapsed_time,
            self.damage_taken,
            success,
        )
        score = self._result_score(self.elapsed_time, self.damage_taken)
        result = {
            "level_index": self.current_level_index,
            "level_name": self.current_level.name,
            "success": success,
            "stars": stars,
            "score": score,
            "time": self.elapsed_time,
            "damage": self.damage_taken,
            "kills": self.total_kills,
        }
        self.level_result = result
        self.level_result_open = True
        self._update_best_result(self.current_level_index, result)

    def _star_text(self, stars: int) -> str:
        return f"{max(0, min(3, stars))}/3"

    def _screen_to_world_pos(self, pos: tuple[int, int]) -> tuple[float, float]:
        if not self.fullscreen:
            return float(pos[0]), float(pos[1])

        display_w, display_h = self.display_size
        if display_w == 0 or display_h == 0:
            return float(pos[0]), float(pos[1])

        scale_x = SCREEN_WIDTH / display_w
        scale_y = SCREEN_HEIGHT / display_h
        return pos[0] * scale_x, pos[1] * scale_y

    def _ui_overlay_open(self) -> bool:
        return self.menu_open or self.level_select_open or self.settings_open or self.level_result_open

    def _present(self) -> None:
        if self.fullscreen or self.display_size != (SCREEN_WIDTH, SCREEN_HEIGHT):
            scaled = pygame.transform.smoothscale(self.screen, self.display_size)
            self.display.blit(scaled, (0, 0))
        else:
            self.display.blit(self.screen, (0, 0))
        pygame.display.flip()

    def _build_path_tiles(self, points: list[tuple[int, int]]) -> set[tuple[int, int]]:
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

    def _cell_center(self, col: int, row: int) -> tuple[float, float]:
        return col * CELL_SIZE + CELL_SIZE / 2, row * CELL_SIZE + CELL_SIZE / 2

    def _tile_for_pos(self, x: float, y: float) -> tuple[int, int]:
        return int(x // CELL_SIZE), int(y // CELL_SIZE)

    def _occupied_tiles(self) -> set[tuple[int, int]]:
        occupied: set[tuple[int, int]] = set()
        for tower in self.towers:
            occupied.add(self._tile_for_pos(tower.x, tower.y))
        return occupied

    def start_wave(self) -> None:
        if self.in_wave or self.game_over or self.victory:
            return
        if self.wave_number >= self.current_level.waves:
            return

        self.in_wave = True
        self.wave_number += 1
        self.wave_spawned = 0
        self.wave_kills = 0
        self.wave_to_spawn = 7 + self.wave_number * 3
        self.spawn_interval = max(0.22, 0.84 - self.wave_number * 0.045)
        self.spawn_cooldown = 0.0

    def _spawn_enemy(self) -> None:
        sx, sy = self.waypoints[0]

        hp = (88 + self.wave_number * 26 + random.randint(-12, 20)) * self.current_level.enemy_hp_mult
        speed = (52 + self.wave_number * 3.8) * self.current_level.enemy_speed_mult
        reward = 8 + self.wave_number // 2
        damage = 1
        radius = 16
        variant = "scout"
        color = (89, 224, 127)

        roll = random.random()
        if roll < 0.18 + self.wave_number * 0.012:
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

        self.enemies.append(
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

    def _target_angle(self, tower: Tower, enemy: Enemy) -> float:
        return math.atan2(enemy.y - tower.y, enemy.x - tower.x)

    def _choose_target(self, tower: Tower) -> Enemy | None:
        r2 = tower.stats.range_px * tower.stats.range_px
        best: Enemy | None = None
        best_progress = -1.0
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            if distance_sq(tower.x, tower.y, enemy.x, enemy.y) > r2:
                continue
            if enemy.path_progress > best_progress:
                best = enemy
                best_progress = enemy.path_progress
        return best

    def _apply_hit(self, target: Enemy, stats: TowerStats, damage: float) -> None:
        if not target.alive:
            return

        died = target.take_damage(damage)
        if stats.slow_duration > 0:
            target.apply_slow(stats.slow_factor, stats.slow_duration)

        if stats.splash_radius > 0:
            sr2 = stats.splash_radius * stats.splash_radius
            for other in self.enemies:
                if other is target or not other.alive:
                    continue
                if distance_sq(target.x, target.y, other.x, other.y) <= sr2:
                    splash_kill = other.take_damage(damage * 0.55)
                    if splash_kill:
                        self._register_enemy_kill(other)

        if died:
            self._register_enemy_kill(target)

    def _place_tower(self, mx: float, my: float) -> None:
        if self.selected_tower_type is None or self.game_over or self.victory:
            return
        if not (0 <= mx < FIELD_WIDTH and 0 <= my < FIELD_HEIGHT):
            return

        col = int(mx // CELL_SIZE)
        row = int(my // CELL_SIZE)
        tile = (col, row)

        if col < 0 or row < 0 or col >= GRID_COLS or row >= GRID_ROWS:
            return
        if tile in self.path_tiles:
            return
        if tile in self._occupied_tiles():
            return
        if self._find_obstacle(col, row) is not None:
            return

        stats = TOWER_TYPES[self.selected_tower_type]
        if self.money < stats.cost:
            return

        self.money -= stats.cost
        x, y = self._cell_center(col, row)
        self.towers.append(Tower(x=x, y=y, tower_type=self.selected_tower_type, stats=stats))

    def _remove_obstacle(self, obstacle: dict[str, object]) -> bool:
        cost = self.current_level.obstacle_cost
        if self.money < cost:
            return False

        self.money -= cost
        self.obstacles.remove(obstacle)
        return True

    def _register_enemy_kill(self, enemy: Enemy) -> None:
        self.money += enemy.reward
        self.total_kills += 1
        self.wave_kills += 1

    def _handle_click(self, mx: float, my: float) -> None:
        if not self._ui_overlay_open() and self.menu_button_rect.collidepoint(mx, my):
            self.open_menu()
            return

        if self.menu_open:
            if self.menu_close_rect and self.menu_close_rect.collidepoint(mx, my):
                self.menu_open = False
                return
            if self.menu_buttons["start"].collidepoint(mx, my):
                self.start_game(self.menu_selected_level)
                return
            if self.menu_buttons["levels"].collidepoint(mx, my):
                self.menu_open = False
                self.level_select_open = True
                return
            if self.menu_buttons["settings"].collidepoint(mx, my):
                self.menu_open = False
                self.settings_open = True
                return
            if self.menu_buttons["exit"].collidepoint(mx, my):
                pygame.quit()
                sys.exit(0)
                return
            return

        if self.level_select_open:
            if (
                self.level_select_close_rect is not None
                and self.level_select_close_rect.collidepoint(mx, my)
            ):
                self.level_select_open = False
                self.menu_open = True
                return
            if self.level_select_buttons["level_0"].collidepoint(mx, my):
                self.menu_selected_level = 0
                return
            if self.level_select_buttons["level_1"].collidepoint(mx, my):
                self.menu_selected_level = 1
                return
            if self.level_select_buttons["level_2"].collidepoint(mx, my):
                self.menu_selected_level = 2
                return
            if self.level_select_buttons["back"].collidepoint(mx, my):
                self.level_select_open = False
                self.menu_open = True
                return
            if self.level_select_buttons["start"].collidepoint(mx, my):
                self.start_game(self.menu_selected_level)
                return
            return

        if self.settings_open:
            if (
                self.settings_close_rect is not None
                and self.settings_close_rect.collidepoint(mx, my)
            ):
                self.settings_open = False
                self.menu_open = True
                return
            if self.settings_buttons["fullscreen"].collidepoint(mx, my):
                self._toggle_fullscreen()
                return
            if self.settings_buttons["back"].collidepoint(mx, my):
                self.settings_open = False
                self.menu_open = True
                return
            return

        if self.info_modal_open:
            if self.info_modal_close_rect and self.info_modal_close_rect.collidepoint(mx, my):
                self._close_info_modal()
                return
            if (
                self.info_modal_action_rect is not None
                and self.info_modal_action_rect.collidepoint(mx, my)
                and self.info_modal_kind == "obstacle"
                and self.info_modal_obstacle is not None
            ):
                self._remove_obstacle(self.info_modal_obstacle)
                self._close_info_modal()
                return
            return

        if 0 <= mx < FIELD_WIDTH and 0 <= my < FIELD_HEIGHT:
            col = int(mx // CELL_SIZE)
            row = int(my // CELL_SIZE)
            obstacle = self._find_obstacle(col, row)
            if obstacle is not None:
                self._open_info_modal(
                    "obstacle",
                    str(obstacle["type"]),
                    obstacle,
                )
                return

        for button in self.buttons:
            rect = button["rect"]
            if not rect.collidepoint(mx, my):
                continue

            if button["kind"] == "tower":
                self.selected_tower_type = button["tower_key"]
                return

            if button["kind"] == "wave":
                self.start_wave()
                return

        self._place_tower(mx, my)

    def _advance_level(self) -> None:
        next_level = self.current_level_index + 1
        if next_level >= len(LEVELS):
            self.victory = True
            self.level_result_open = False
            return

        self.reset_round(next_level)

    def _handle_right_click(self, mx: float, my: float) -> bool:
        for button in self.buttons:
            if button["kind"] != "tower":
                continue
            rect = button["rect"]
            if rect.collidepoint(mx, my):
                self.selected_tower_type = button["tower_key"]
                self._open_info_modal("tower", str(button["tower_key"]))
                return True
        return False

    def _restart_current_level(self) -> None:
        self.reset_round(self.current_level_index)

    def _update_stars(self, dt: float) -> None:
        if self.current_level.theme != "desert":
            return

        for star in self.stars:
            star[0] -= star[2] * dt
            if star[0] < 0:
                star[0] = FIELD_WIDTH + random.uniform(4, 36)
                star[1] = random.uniform(0, FIELD_HEIGHT)

    def update(self, dt: float) -> None:
        self.elapsed_time += dt
        self._update_stars(dt)

        if self.menu_open or self.level_select_open or self.settings_open or self.level_result_open:
            return

        if self.game_over or self.victory:
            return

        if self.in_wave:
            self.spawn_cooldown -= dt
            if self.wave_spawned < self.wave_to_spawn and self.spawn_cooldown <= 0:
                self._spawn_enemy()
                self.wave_spawned += 1
                self.spawn_cooldown = self.spawn_interval

        for enemy in self.enemies:
            reached_base = enemy.update(dt, self.waypoints)
            if reached_base and enemy.alive:
                enemy.hp = 0
                self.lives -= enemy.damage
                self.damage_taken += enemy.damage

        for tower in self.towers:
            tower.update(dt)
            if tower.cooldown > 0:
                continue

            target = self._choose_target(tower)
            if target is None:
                continue

            tower.aim_angle = self._target_angle(tower, target)
            tower.recoil_timer = 0.16

            self.projectiles.append(
                Projectile(
                    x=tower.x,
                    y=tower.y,
                    target=target,
                    stats=tower.stats,
                    damage=tower.stats.damage,
                    speed=tower.stats.projectile_speed,
                    color=tower.stats.color,
                )
            )
            tower.cooldown = 1.0 / tower.stats.fire_rate

        to_remove: list[Projectile] = []
        for projectile in self.projectiles:
            hit_target = projectile.update(dt)
            if hit_target:
                if projectile.target is not None and projectile.target.alive:
                    self._apply_hit(projectile.target, projectile.stats, projectile.damage)
                to_remove.append(projectile)

        for projectile in to_remove:
            if projectile in self.projectiles:
                self.projectiles.remove(projectile)

        self.enemies = [enemy for enemy in self.enemies if enemy.alive]

        if self.in_wave and self.wave_spawned >= self.wave_to_spawn and not self.enemies:
            self.in_wave = False
            if self.wave_number >= self.current_level.waves:
                self._trigger_level_result(success=True)

        if self.lives <= 0:
            self.game_over = True
            self._trigger_level_result(success=False)

    def _draw_background(self) -> None:
        self._draw_theme_background()

        if self.current_level.theme == "desert":
            for sx, sy, _, size in self.stars:
                pygame.draw.circle(self.screen, (220, 232, 255), (int(sx), int(sy)), int(size))

    def _draw_grid(self) -> None:
        grid_color = (255, 255, 255, 20)
        grid_surface = pygame.Surface((FIELD_WIDTH, FIELD_HEIGHT), pygame.SRCALPHA)
        for col in range(GRID_COLS + 1):
            x = col * CELL_SIZE
            pygame.draw.line(grid_surface, grid_color, (x, 0), (x, FIELD_HEIGHT), 1)
        for row in range(GRID_ROWS + 1):
            y = row * CELL_SIZE
            pygame.draw.line(grid_surface, grid_color, (0, y), (FIELD_WIDTH, y), 1)
        self.screen.blit(grid_surface, (0, 0))

    def _draw_path(self) -> None:
        for col, row in self.path_tiles:
            rect = pygame.Rect(col * CELL_SIZE, row * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(self.screen, self._theme_path_tint(), rect, border_radius=6)

        sx, sy = self.waypoints[0]
        ex, ey = self.waypoints[-1]

        ufo_y = sy + math.sin(self.elapsed_time * 2.4) * 6
        pygame.draw.ellipse(self.screen, (190, 220, 255), (sx - 28, ufo_y - 12, 56, 24))
        pygame.draw.ellipse(self.screen, (120, 156, 212), (sx - 16, ufo_y - 22, 32, 16))

        self._draw_goal_sprite(ex, ey)

        self._draw_level_decor()

    def _draw_goal_sprite(self, x: float, y: float) -> None:
        goal = self.current_level.goal
        cx = int(x)
        cy = int(y)

        if goal == "База людей":
            base_rect = pygame.Rect(cx - 24, cy - 24, 48, 48)
            pygame.draw.rect(self.screen, (228, 216, 170), base_rect, border_radius=7)
            pygame.draw.rect(self.screen, (171, 148, 96), base_rect, 2, border_radius=7)
            pygame.draw.rect(self.screen, (120, 156, 212), (cx - 8, cy - 38, 16, 16), border_radius=4)
        elif goal == "Домик в деревне":
            pygame.draw.rect(self.screen, (164, 124, 88), (cx - 20, cy - 12, 40, 28), border_radius=4)
            pygame.draw.polygon(self.screen, (124, 68, 50), [(cx - 28, cy - 10), (cx, cy - 34), (cx + 28, cy - 10)])
            pygame.draw.rect(self.screen, (90, 70, 42), (cx - 6, cy + 4, 12, 12))
        else:
            pygame.draw.rect(self.screen, (92, 106, 136), (cx - 30, cy - 18, 60, 44), border_radius=6)
            pygame.draw.rect(self.screen, (152, 180, 210), (cx - 12, cy - 36, 24, 18), border_radius=4)
            pygame.draw.rect(self.screen, (68, 78, 96), (cx - 18, cy + 2, 36, 6), border_radius=3)

    def _draw_obstacles(self) -> None:
        for obstacle in self.obstacles:
            rect = cast(pygame.Rect, obstacle["rect"])
            obstacle_type = obstacle["type"]
            if obstacle_type == "rock":
                pygame.draw.circle(self.screen, (106, 96, 82), rect.center, rect.width // 2)
                pygame.draw.circle(self.screen, (138, 126, 103), (rect.centerx - 6, rect.centery - 4), 6)
            elif obstacle_type == "tree":
                pygame.draw.rect(self.screen, (90, 66, 40), (rect.centerx - 4, rect.centery, 8, rect.height // 2))
                pygame.draw.circle(self.screen, (54, 124, 68), (rect.centerx, rect.centery - 6), rect.width // 2)
            elif obstacle_type == "scrap":
                pygame.draw.rect(self.screen, (114, 116, 128), rect, border_radius=6)
                pygame.draw.line(self.screen, (156, 160, 176), rect.topleft, rect.bottomright, 3)
            elif obstacle_type == "hay":
                pygame.draw.polygon(self.screen, (184, 154, 74), [(rect.left, rect.bottom), (rect.centerx, rect.top), (rect.right, rect.bottom)])
            elif obstacle_type == "fence":
                pygame.draw.rect(self.screen, (138, 108, 68), rect, border_radius=4)
                pygame.draw.line(self.screen, (168, 138, 94), (rect.left, rect.centery), (rect.right, rect.centery), 4)
            elif obstacle_type == "building":
                pygame.draw.rect(self.screen, (74, 82, 102), rect, border_radius=4)
                pygame.draw.rect(self.screen, (128, 140, 168), rect.inflate(-20, -20), border_radius=4)
            elif obstacle_type == "car":
                pygame.draw.rect(self.screen, (82, 90, 98), rect.inflate(-4, 6), border_radius=6)
                pygame.draw.circle(self.screen, (28, 28, 32), (rect.left + 10, rect.bottom - 6), 5)
                pygame.draw.circle(self.screen, (28, 28, 32), (rect.right - 10, rect.bottom - 6), 5)
            elif obstacle_type == "streetlight":
                pygame.draw.line(self.screen, (170, 170, 180), (rect.centerx, rect.bottom), (rect.centerx, rect.top), 4)
                pygame.draw.circle(self.screen, (255, 226, 142), (rect.centerx + 12, rect.top + 10), 5)

    def _draw_towers(self) -> None:
        for tower in self.towers:
            self._draw_tower_sprite(tower, False)

        if self.selected_tower_type is None or self._ui_overlay_open():
            return

        mx, my = self._screen_to_world_pos(pygame.mouse.get_pos())
        if not (0 <= mx < FIELD_WIDTH and 0 <= my < FIELD_HEIGHT):
            return

        col = int(mx // CELL_SIZE)
        row = int(my // CELL_SIZE)
        x, y = self._cell_center(col, row)
        tile = (col, row)

        valid = tile not in self.path_tiles and tile not in self._occupied_tiles()
        tint = (80, 220, 130, 110) if valid else (220, 80, 80, 110)

        preview = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        pygame.draw.rect(preview, tint, preview.get_rect(), border_radius=10)
        self.screen.blit(preview, (col * CELL_SIZE, row * CELL_SIZE))

        tower_stats = TOWER_TYPES[self.selected_tower_type]
        range_surface = pygame.Surface((FIELD_WIDTH, FIELD_HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(
            range_surface,
            (
                tower_stats.color[0],
                tower_stats.color[1],
                tower_stats.color[2],
                38,
            ),
            (int(x), int(y)),
            int(tower_stats.range_px),
            width=2,
        )
        self.screen.blit(range_surface, (0, 0))

    def _draw_tower_sprite(self, tower: Tower, is_preview: bool = False) -> None:
        x = int(tower.x)
        y = int(tower.y)
        base_color = (24, 28, 42)
        accent = tower.stats.color
        wobble = math.sin(self.elapsed_time * 5.0 + (x + y) * 0.01) * 0.08 if not is_preview else 0.0
        barrel_angle = tower.aim_angle + wobble
        recoil = min(1.0, tower.recoil_timer * 4.0) if tower.recoil_timer > 0 else 0.0

        def rotate_point(px: float, py: float) -> tuple[int, int]:
            cos_a = math.cos(barrel_angle)
            sin_a = math.sin(barrel_angle)
            return int(x + px * cos_a - py * sin_a), int(y + px * sin_a + py * cos_a)

        if tower.tower_type == "blaster":
            pygame.draw.circle(self.screen, base_color, (x, y), 18)
            pygame.draw.circle(self.screen, accent, (x, y), 14)
            barrel = [
                rotate_point(5 + recoil * 6, -4),
                rotate_point(23 + recoil * 10, -4),
                rotate_point(23 + recoil * 10, 4),
                rotate_point(5 + recoil * 6, 4),
            ]
            pygame.draw.polygon(self.screen, (230, 236, 244), barrel)
            pygame.draw.circle(self.screen, (10, 12, 20), (x, y), 5)
        elif tower.tower_type == "frost":
            points = [rotate_point(0, -18), rotate_point(16, 0), rotate_point(0, 18), rotate_point(-16, 0)]
            pygame.draw.polygon(self.screen, base_color, points)
            inner = [rotate_point(0, -13), rotate_point(12, 0), rotate_point(0, 13), rotate_point(-12, 0)]
            pygame.draw.polygon(self.screen, accent, inner)
            pygame.draw.circle(self.screen, (236, 248, 255), (x, y), 4)
        else:
            body = [rotate_point(-18, -10), rotate_point(0, -20), rotate_point(18, -10), rotate_point(18, 10), rotate_point(0, 20), rotate_point(-18, 10)]
            core = [rotate_point(-12, -7), rotate_point(0, -14), rotate_point(12, -7), rotate_point(12, 7), rotate_point(0, 14), rotate_point(-12, 7)]
            pygame.draw.polygon(self.screen, base_color, body)
            pygame.draw.polygon(self.screen, accent, core)
            pygame.draw.circle(self.screen, (255, 245, 232), (x, y), 4)

        if is_preview:
            pygame.draw.circle(self.screen, (255, 255, 255, 45), (x, y), 24, width=1)

    def _draw_enemy_sprite(self, enemy: Enemy) -> None:
        x = int(enemy.x)
        y = int(enemy.y)

        if enemy.variant == "brute":
            pygame.draw.circle(self.screen, (20, 24, 30), (x, y), int(enemy.radius) + 5)
            pygame.draw.circle(self.screen, enemy.color, (x, y), int(enemy.radius))
            pygame.draw.rect(self.screen, (255, 214, 174), (x - 6, y - 4, 12, 8), border_radius=3)
            pygame.draw.circle(self.screen, (17, 18, 22), (x - 7, y - 5), 2)
            pygame.draw.circle(self.screen, (17, 18, 22), (x + 7, y - 5), 2)
        elif enemy.variant == "stalker":
            points = [(x, y - int(enemy.radius) - 6), (x + int(enemy.radius) + 6, y), (x, y + int(enemy.radius) + 6), (x - int(enemy.radius) + 6, y)]
            pygame.draw.polygon(self.screen, (20, 24, 30), points)
            pygame.draw.polygon(self.screen, enemy.color, [(x, y - int(enemy.radius)), (x + int(enemy.radius), y), (x, y + int(enemy.radius)), (x - int(enemy.radius), y)])
            pygame.draw.circle(self.screen, (235, 245, 255), (x, y), 3)
        else:
            pygame.draw.circle(self.screen, (18, 24, 32), (x, y), int(enemy.radius) + 4)
            pygame.draw.circle(self.screen, enemy.color, (x, y), int(enemy.radius))
            pygame.draw.polygon(self.screen, (255, 255, 255), [(x, y - 8), (x + 4, y), (x, y + 3), (x - 4, y)])

    def _draw_enemies(self) -> None:
        for enemy in self.enemies:
            self._draw_enemy_sprite(enemy)

            bar_w = int(enemy.radius * 2.2)
            bar_h = 5
            hx = int(enemy.x - bar_w / 2)
            hy = int(enemy.y - enemy.radius - 12)
            pygame.draw.rect(self.screen, (52, 53, 58), (hx, hy, bar_w, bar_h), border_radius=3)
            hp_ratio = max(0.0, enemy.hp / enemy.max_hp)
            pygame.draw.rect(
                self.screen,
                SUCCESS if hp_ratio > 0.4 else DANGER,
                (hx, hy, int(bar_w * hp_ratio), bar_h),
                border_radius=3,
            )

    def _draw_projectiles(self) -> None:
        for p in self.projectiles:
            pygame.draw.circle(self.screen, p.color, (int(p.x), int(p.y)), 4)

    def _draw_menu_button(self) -> None:
        if self.menu_open or self.level_select_open or self.settings_open or self.level_result_open:
            return

        rect = self.menu_button_rect
        pygame.draw.rect(self.screen, (39, 46, 68), rect, border_radius=10)
        pygame.draw.rect(self.screen, (150, 185, 255), rect, 2, border_radius=10)
        icon = pygame.Rect(rect.x + 10, rect.y + 8, 18, 18)
        pygame.draw.rect(self.screen, (255, 198, 78), icon, border_radius=4)
        pygame.draw.polygon(
            self.screen,
            (255, 236, 197),
            [(icon.left - 1, icon.bottom), (icon.centerx, icon.top - 6), (icon.right + 1, icon.bottom)],
        )
        text = self.small_font.render("Меню", True, TEXT)
        self.screen.blit(text, (rect.x + 34, rect.y + 8))

    def _draw_sidebar(self) -> None:
        panel = pygame.Rect(FIELD_WIDTH, 0, SIDEBAR_WIDTH, SCREEN_HEIGHT)
        pygame.draw.rect(self.screen, (18, 21, 32), panel)
        pygame.draw.line(self.screen, (55, 66, 97), (FIELD_WIDTH, 0), (FIELD_WIDTH, SCREEN_HEIGHT), 2)

        title = self.big_font.render("ВТОРЖЕНИЕ", True, ACCENT)
        self.screen.blit(title, (FIELD_WIDTH + 20, 18))

        info_lines = [
            f"Уровень: {self.current_level.name}",
            f"Деньги: {self.money}",
            f"Жизни: {self.lives}",
            f"Волна: {self.wave_number}/{self.current_level.waves}",
            f"Убийства: {self.total_kills}",
        ]
        y = 68
        for line in info_lines:
            txt = self.small_font.render(line, True, TEXT)
            self.screen.blit(txt, (FIELD_WIDTH + 24, y))
            y += 22

        best = self.best_results.get(str(self.current_level_index), {})
        best_stars = int(best.get("best_stars", 0)) if isinstance(best, dict) else 0
        best_time = float(best.get("best_time", 0.0)) if isinstance(best, dict) else 0.0
        best_line = f"Лучшее: {self._star_text(best_stars)} {self._formatted_time(best_time)}"
        best_txt = self.small_font.render(best_line, True, ACCENT)
        self.screen.blit(best_txt, (FIELD_WIDTH + 24, 176))

        goal_line = f"Цель: {self.current_level.goal}"
        goal_txt = self.small_font.render(goal_line, True, (235, 241, 250))
        self.screen.blit(goal_txt, (FIELD_WIDTH + 24, 206))

        completed_waves = self.wave_number - (1 if self.in_wave else 0)
        waves_line = f"Пройдено волн: {completed_waves}/{self.current_level.waves}"
        waves_txt = self.small_font.render(waves_line, True, (235, 241, 250))
        self.screen.blit(waves_txt, (FIELD_WIDTH + 24, 234))

        for button in self.buttons:
            rect: pygame.Rect = button["rect"]
            if button["kind"] == "tower":
                tower_key = button["tower_key"]
                stats = TOWER_TYPES[tower_key]
                selected = tower_key == self.selected_tower_type

                color = (54, 61, 88) if not selected else (83, 96, 140)
                pygame.draw.rect(self.screen, color, rect, border_radius=9)
                pygame.draw.rect(self.screen, stats.color, rect, 2, border_radius=9)

                icon_tower = Tower(x=rect.x + 28, y=rect.y + 30, tower_type=tower_key, stats=stats)
                self._draw_tower_sprite(icon_tower, True)

                text_x = rect.x + 88
                line1 = self.font.render(stats.name, True, TEXT)
                line2 = self.small_font.render(
                    f"${stats.cost} • Урон {int(stats.damage)}",
                    True,
                    (208, 214, 226),
                )
                self.screen.blit(line1, (text_x, rect.y + 8))
                self.screen.blit(line2, (text_x, rect.y + 32))
            if button["kind"] == "wave":
                disabled = self.in_wave or self.game_over or self.victory or self.wave_number >= self.current_level.waves
                color = (70, 113, 87) if not disabled else (60, 67, 78)
                pygame.draw.rect(self.screen, color, rect, border_radius=10)
                pygame.draw.rect(self.screen, (121, 186, 145), rect, 2, border_radius=10)
                label = "Волна идёт" if self.in_wave else "Начать волну"
                txt = self.font.render(label, True, TEXT)
                self.screen.blit(txt, (rect.x + 22, rect.y + 18))

        wave_rect = None
        for button in self.buttons:
            if button["kind"] == "wave":
                wave_rect = button["rect"]
                break

        if wave_rect is not None:
            if self.wave_number == 0:
                wave_status = f"Следующая волна: 1/{self.current_level.waves}"
            elif self.in_wave:
                wave_status = f"Волна: {self.wave_number}/{self.current_level.waves}"
            elif self.wave_number < self.current_level.waves:
                wave_status = f"Следующая волна: {self.wave_number + 1}/{self.current_level.waves}"
            else:
                wave_status = f"Все волны пройдены"

            status_txt = self.small_font.render(wave_status, True, (208, 214, 226))
            self.screen.blit(status_txt, (wave_rect.x + 12, wave_rect.bottom + 16))

            if self.wave_to_spawn > 0:
                progress_rect = pygame.Rect(wave_rect.x, wave_rect.bottom + 42, wave_rect.width, 18)
                pygame.draw.rect(self.screen, (32, 38, 56), progress_rect, border_radius=10)
                ratio = min(1.0, self.wave_kills / self.wave_to_spawn)
                fill_width = int((progress_rect.width - 4) * ratio)
                if fill_width > 0:
                    fill_rect = pygame.Rect(
                        progress_rect.x + 2,
                        progress_rect.y + 2,
                        fill_width,
                        progress_rect.height - 4,
                    )
                    pygame.draw.rect(self.screen, (121, 186, 145), fill_rect, border_radius=8)

                wave_text = f"{self.wave_kills}/{self.wave_to_spawn}"
                wave_txt = self.small_font.render(wave_text, True, TEXT)
                self.screen.blit(wave_txt, (wave_rect.x + wave_rect.width - wave_txt.get_width() - 12, progress_rect.y + 1))

    def _draw_info_modal(self) -> None:
        if not self.info_modal_open or self.info_modal_kind is None:
            return

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 10, 16, 185))
        self.screen.blit(overlay, (0, 0))

        panel_w = 430
        panel_h = 248 if self.info_modal_kind == "tower" else 238
        panel = pygame.Rect(
            SCREEN_WIDTH // 2 - panel_w // 2,
            SCREEN_HEIGHT // 2 - panel_h // 2,
            panel_w,
            panel_h,
        )
        self.info_modal_rect = panel

        if self.info_modal_kind == "tower" and self.info_modal_value is not None:
            self.info_modal_action_rect = None
            stats = TOWER_TYPES[self.info_modal_value]
            title_text = stats.name
            border = stats.color
            desc = TOWER_DESCRIPTIONS[self.info_modal_value]
            remove_text = ""
        else:
            border = (146, 124, 78)
            obstacle_key = str(self.info_modal_value or "")
            title_text = OBSTACLE_NAMES.get(obstacle_key, "Препятствие")
            obstacle_name = OBSTACLE_NAMES.get(obstacle_key, obstacle_key)
            desc = (
                f"Тип: {obstacle_name}"
                f"\nУдалить можно за ${self.current_level.obstacle_cost}."
            )
            remove_text = "Убрать за деньги"

        pygame.draw.rect(self.screen, (25, 30, 44), panel, border_radius=14)
        pygame.draw.rect(self.screen, border, panel, 2, border_radius=14)

        close_rect = pygame.Rect(panel.right - 38, panel.y + 10, 24, 24)
        self.info_modal_close_rect = close_rect
        pygame.draw.rect(self.screen, (88, 92, 110), close_rect, border_radius=6)
        pygame.draw.line(self.screen, TEXT, (close_rect.left + 6, close_rect.top + 6), (close_rect.right - 6, close_rect.bottom - 6), 2)
        pygame.draw.line(self.screen, TEXT, (close_rect.left + 6, close_rect.bottom - 6), (close_rect.right - 6, close_rect.top + 6), 2)

        title = self.font.render(title_text, True, ACCENT)
        self.screen.blit(title, (panel.x + 18, panel.y + 14))

        wrapped = textwrap.wrap(desc, width=34)
        y = panel.y + 62
        for line in wrapped[:4]:
            text = self.small_font.render(line, True, TEXT)
            self.screen.blit(text, (panel.x + 18, y))
            y += 22

        if self.info_modal_kind == "tower" and self.info_modal_value is not None:
            stats = TOWER_TYPES[self.info_modal_value]
            stat_line1 = f"Урон: {int(stats.damage)}   Дальность: {int(stats.range_px)}"
            stat_line2 = f"Скорострельность: {stats.fire_rate:.1f}"
            stat_text1 = self.small_font.render(stat_line1, True, (208, 214, 226))
            stat_text2 = self.small_font.render(stat_line2, True, (208, 214, 226))
            self.screen.blit(stat_text1, (panel.x + 18, panel.bottom - 74))
            self.screen.blit(stat_text2, (panel.x + 18, panel.bottom - 44))
        else:
            action_rect = pygame.Rect(panel.x + 18, panel.bottom - 54, panel.width - 36, 36)
            self.info_modal_action_rect = action_rect
            pygame.draw.rect(self.screen, (88, 130, 92), action_rect, border_radius=9)
            pygame.draw.rect(self.screen, (150, 213, 169), action_rect, 2, border_radius=9)
            action_text = self.small_font.render(remove_text, True, TEXT)
            self.screen.blit(action_text, (action_rect.centerx - action_text.get_width() // 2, action_rect.y + 9))

    def _draw_settings_overlay(self) -> None:
        if not self.settings_open:
            return
        if self.settings_close_rect is None:
            return

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 11, 20, 180))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(SCREEN_WIDTH // 2 - 300, SCREEN_HEIGHT // 2 - 215, 600, 430)
        pygame.draw.rect(self.screen, (26, 31, 46), panel, border_radius=14)
        pygame.draw.rect(self.screen, (103, 124, 176), panel, 2, border_radius=14)

        title = self.font.render("Настройки", True, TEXT)
        self.screen.blit(title, (panel.x + 245, panel.y + 18))

        close_rect = self.settings_close_rect
        pygame.draw.rect(self.screen, (88, 92, 110), close_rect, border_radius=6)
        pygame.draw.line(self.screen, TEXT, (close_rect.left + 6, close_rect.top + 6), (close_rect.right - 6, close_rect.bottom - 6), 2)
        pygame.draw.line(self.screen, TEXT, (close_rect.left + 6, close_rect.bottom - 6), (close_rect.right - 6, close_rect.top + 6), 2)

        fs_rect = self.settings_buttons["fullscreen"]
        back_rect = self.settings_buttons["back"]

        pygame.draw.rect(self.screen, (54, 74, 110), fs_rect, border_radius=10)
        pygame.draw.rect(self.screen, (143, 176, 247), fs_rect, 2, border_radius=10)
        mode_text = "Полноэкранный: ВКЛ" if self.fullscreen else "Полноэкранный: ВЫКЛ"
        fs_txt = self.font.render(mode_text, True, TEXT)
        self.screen.blit(fs_txt, (fs_rect.centerx - fs_txt.get_width() // 2, fs_rect.y + 18))

        controls_title = self.font.render("Управление", True, ACCENT)
        self.screen.blit(controls_title, (panel.x + 26, panel.y + 182))

        controls = [
            "ЛКМ: выбор и установка башни",
            "ПКМ: снять выбор башни",
            "F11: переключение полноэкранного режима",
            "R: перезапуск после победы или поражения",
        ]
        y = panel.y + 226
        for line in controls:
            text = self.small_font.render(line, True, (208, 214, 226))
            self.screen.blit(text, (panel.x + 28, y))
            y += 28

        pygame.draw.rect(self.screen, (61, 99, 79), back_rect, border_radius=10)
        pygame.draw.rect(self.screen, (143, 213, 169), back_rect, 2, border_radius=10)
        back_txt = self.font.render("Назад", True, TEXT)
        self.screen.blit(back_txt, (back_rect.x + 62, back_rect.y + 14))

    def _draw_menu_overlay(self) -> None:
        if not self.menu_open:
            return
        if self.menu_close_rect is None:
            return

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((7, 10, 18, 175))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(SCREEN_WIDTH // 2 - 320, SCREEN_HEIGHT // 2 - 240, 640, 480)
        pygame.draw.rect(self.screen, (24, 29, 43), panel, border_radius=18)
        pygame.draw.rect(self.screen, (118, 143, 196), panel, 2, border_radius=18)

        title = self.big_font.render("ВТОРЖЕНИЕ", True, ACCENT)
        self.screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 22))

        close_rect = self.menu_close_rect
        pygame.draw.rect(self.screen, (88, 92, 110), close_rect, border_radius=6)
        pygame.draw.line(self.screen, TEXT, (close_rect.left + 6, close_rect.top + 6), (close_rect.right - 6, close_rect.bottom - 6), 2)
        pygame.draw.line(self.screen, TEXT, (close_rect.left + 6, close_rect.bottom - 6), (close_rect.right - 6, close_rect.top + 6), 2)

        subtitle = self.font.render("Главное меню", True, TEXT)
        self.screen.blit(subtitle, (panel.centerx - subtitle.get_width() // 2, panel.y + 92))

        hint = self.small_font.render("F11 переключает полноэкранный режим", True, (190, 198, 214))
        self.screen.blit(hint, (panel.centerx - hint.get_width() // 2, panel.y + 116))

        for key, label in [
            ("start", "Продолжить / Старт"),
            ("levels", "Выбор уровня"),
            ("settings", "Настройки"),
            ("exit", "Выход"),
        ]:
            rect = self.menu_buttons[key]
            color = (66, 95, 132) if key != "exit" else (122, 58, 58)
            edge = (150, 185, 255) if key != "exit" else (245, 134, 134)
            pygame.draw.rect(self.screen, color, rect, border_radius=12)
            pygame.draw.rect(self.screen, edge, rect, 2, border_radius=12)
            text = self.font.render(label, True, TEXT)
            self.screen.blit(text, (rect.centerx - text.get_width() // 2, rect.y + 18))

    def _draw_level_select_overlay(self) -> None:
        if not self.level_select_open:
            return
        if self.level_select_close_rect is None:
            return

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((7, 10, 18, 175))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(SCREEN_WIDTH // 2 - 320, SCREEN_HEIGHT // 2 - 240, 640, 480)
        pygame.draw.rect(self.screen, (24, 29, 43), panel, border_radius=18)
        pygame.draw.rect(self.screen, (118, 143, 196), panel, 2, border_radius=18)

        title = self.big_font.render("Выбор уровня", True, ACCENT)
        self.screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 20))

        close_rect = self.level_select_close_rect
        pygame.draw.rect(self.screen, (88, 92, 110), close_rect, border_radius=6)
        pygame.draw.line(self.screen, TEXT, (close_rect.left + 6, close_rect.top + 6), (close_rect.right - 6, close_rect.bottom - 6), 2)
        pygame.draw.line(self.screen, TEXT, (close_rect.left + 6, close_rect.bottom - 6), (close_rect.right - 6, close_rect.top + 6), 2)

        for index, level in enumerate(LEVELS):
            rect = self.level_select_buttons[f"level_{index}"]
            selected = index == self.menu_selected_level
            color = (72, 91, 128) if selected else (49, 57, 79)
            edge = (150, 185, 255) if selected else (103, 124, 176)
            pygame.draw.rect(self.screen, color, rect, border_radius=12)
            pygame.draw.rect(self.screen, edge, rect, 2, border_radius=12)

            name = self.font.render(level.name, True, TEXT)
            best = self.best_results.get(str(index), {})
            best_stars = int(best.get("best_stars", 0)) if isinstance(best, dict) else 0
            meta_text = f"Волн: {level.waves}   Лучшее: {self._star_text(best_stars)}"
            meta = self.small_font.render(meta_text, True, (208, 214, 226))
            self.screen.blit(name, (rect.x + 20, rect.y + 10))
            self.screen.blit(meta, (rect.x + 20, rect.y + 36))

        back_rect = self.level_select_buttons["back"]
        start_rect = self.level_select_buttons["start"]
        pygame.draw.rect(self.screen, (61, 99, 79), back_rect, border_radius=10)
        pygame.draw.rect(self.screen, (143, 213, 169), back_rect, 2, border_radius=10)
        back_txt = self.small_font.render("Назад", True, TEXT)
        self.screen.blit(back_txt, (back_rect.centerx - back_txt.get_width() // 2, back_rect.y + 16))

        pygame.draw.rect(self.screen, (66, 95, 132), start_rect, border_radius=10)
        pygame.draw.rect(self.screen, (150, 185, 255), start_rect, 2, border_radius=10)
        start_txt = self.small_font.render("Играть", True, TEXT)
        self.screen.blit(start_txt, (start_rect.centerx - start_txt.get_width() // 2, start_rect.y + 16))

    def _draw_theme_background(self) -> None:
        if self.current_level.theme == "desert":
            top = (20, 16, 34)
            bottom = (14, 12, 24)
            halo = pygame.Surface((FIELD_WIDTH, FIELD_HEIGHT), pygame.SRCALPHA)
            pygame.draw.circle(halo, (134, 125, 191, 40), (FIELD_WIDTH - 90, 90), 82)
            pygame.draw.circle(halo, (255, 206, 118, 40), (FIELD_WIDTH - 130, 130), 48)
            self.screen.blit(halo, (0, 0))
        elif self.current_level.theme == "field":
            top = (20, 44, 38)
            bottom = (14, 24, 22)
            haze = pygame.Surface((FIELD_WIDTH, FIELD_HEIGHT), pygame.SRCALPHA)
            for i in range(5):
                alpha = 22
                pygame.draw.ellipse(haze, (180, 220, 190, alpha), (-60 + i * 100, 20 + i * 28, 220, 70))
            self.screen.blit(haze, (0, 0))
        else:
            top = (12, 18, 38)
            bottom = (6, 10, 22)
            silhouette = pygame.Surface((FIELD_WIDTH, FIELD_HEIGHT), pygame.SRCALPHA)
            for x in range(0, FIELD_WIDTH, 72):
                pygame.draw.rect(silhouette, (16, 18, 30, 190), (x, FIELD_HEIGHT - 84 - (x % 32), 60, 84 + (x % 24)))
            pygame.draw.circle(silhouette, (94, 112, 255, 28), (FIELD_WIDTH - 90, 96), 64)
            self.screen.blit(silhouette, (0, 0))

        for y in range(FIELD_HEIGHT):
            t = y / max(1, FIELD_HEIGHT - 1)
            r = int(top[0] * (1 - t) + bottom[0] * t)
            g = int(top[1] * (1 - t) + bottom[1] * t)
            b = int(top[2] * (1 - t) + bottom[2] * t)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (FIELD_WIDTH, y))

        if self.current_level.theme == "desert":
            for i in range(12):
                star_x = (i * 84 + int(self.elapsed_time * 22)) % FIELD_WIDTH
                star_y = 18 + (i * 13) % 30
                pygame.draw.circle(self.screen, (220, 232, 255), (star_x, star_y), 2)
        elif self.current_level.theme == "city":
            for x in range(16, FIELD_WIDTH, 56):
                spike_y = FIELD_HEIGHT - 90 - ((x // 56) % 3) * 10
                pygame.draw.line(self.screen, (75, 93, 164), (x, spike_y), (x, FIELD_HEIGHT - 70), 3)

    def _theme_path_tint(self) -> tuple[int, int, int]:
        if self.current_level.theme == "desert":
            return (132, 121, 90)
        if self.current_level.theme == "field":
            return (92, 92, 58)
        return (104, 108, 132)

    def _draw_level_decor(self) -> None:
        theme = self.current_level.theme
        for index, item in enumerate(self.current_level.decor):
            if theme == "desert":
                positions = [
                    (16, 18),
                    (FIELD_WIDTH - 138, 24),
                    (24, FIELD_HEIGHT - 88),
                    (FIELD_WIDTH - 130, FIELD_HEIGHT - 72),
                ]
                px, py = positions[index % len(positions)]
                if item == "dune":
                    pygame.draw.arc(self.screen, (170, 154, 98), (px, py, 130, 54), 0.2, 3.0, 5)
                    pygame.draw.arc(self.screen, (138, 125, 74), (px + 24, py + 16, 92, 40), 0.2, 3.0, 4)
                elif item == "rock":
                    pygame.draw.circle(self.screen, (88, 79, 62), (px + 40, py + 42), 18)
                    pygame.draw.circle(self.screen, (117, 102, 79), (px + 56, py + 30), 12)
                elif item == "crater":
                    pygame.draw.ellipse(self.screen, (94, 85, 62), (px, py + 6, 96, 28))
                    pygame.draw.ellipse(self.screen, (56, 49, 40), (px + 16, py + 12, 64, 12))
                else:
                    pygame.draw.line(self.screen, (158, 145, 118), (px + 42, py + 56), (px + 42, py + 10), 4)
                    pygame.draw.circle(self.screen, (188, 177, 150), (px + 42, py + 10), 8)
                    pygame.draw.circle(self.screen, (255, 220, 120), (px + 42, py + 10), 5)
            elif theme == "field":
                positions = [
                    (18, 16),
                    (FIELD_WIDTH - 150, 24),
                    (20, FIELD_HEIGHT - 92),
                    (FIELD_WIDTH - 160, FIELD_HEIGHT - 80),
                ]
                px, py = positions[index % len(positions)]
                if item == "tree":
                    pygame.draw.rect(self.screen, (92, 74, 44), (px + 34, py + 40, 10, 30))
                    pygame.draw.circle(self.screen, (58, 118, 66), (px + 40, py + 30), 22)
                    pygame.draw.circle(self.screen, (86, 154, 84), (px + 26, py + 22), 14)
                    pygame.draw.circle(self.screen, (86, 154, 84), (px + 56, py + 22), 14)
                elif item == "hill":
                    pygame.draw.ellipse(self.screen, (84, 120, 64), (px, py + 34, 128, 40))
                    pygame.draw.ellipse(self.screen, (55, 95, 50), (px + 18, py + 42, 90, 24))
                elif item == "barn":
                    pygame.draw.rect(self.screen, (160, 84, 69), (px + 18, py + 26, 56, 38), border_radius=6)
                    pygame.draw.polygon(self.screen, (122, 53, 52), [(px + 10, py + 28), (px + 44, py + 6), (px + 80, py + 28)])
                    pygame.draw.rect(self.screen, (218, 190, 145), (px + 30, py + 40, 20, 18))
                elif item == "windmill":
                    pygame.draw.rect(self.screen, (120, 85, 50), (px + 46, py + 24, 8, 56))
                    center = (px + 50, py + 26)
                    pygame.draw.line(self.screen, (218, 218, 218), center, (px + 26, py + 38), 4)
                    pygame.draw.line(self.screen, (218, 218, 218), center, (px + 74, py + 38), 4)
                    pygame.draw.line(self.screen, (218, 218, 218), center, (px + 50, py + 10), 4)
                    pygame.draw.line(self.screen, (218, 218, 218), center, (px + 50, py + 52), 4)
                else:
                    pygame.draw.rect(self.screen, (110, 102, 78), (px + 52, py + 16, 8, 44))
                    pygame.draw.line(self.screen, (110, 102, 78), (px + 56, py + 42), (px + 72, py + 36), 3)
                    pygame.draw.line(self.screen, (110, 102, 78), (px + 56, py + 50), (px + 38, py + 42), 3)
            else:
                positions = [
                    (16, 20),
                    (FIELD_WIDTH - 150, 24),
                    (FIELD_WIDTH - 148, FIELD_HEIGHT - 96),
                    (24, FIELD_HEIGHT - 90),
                ]
                px, py = positions[index % len(positions)]
                if item == "building":
                    pygame.draw.rect(self.screen, (66, 72, 92), (px + 18, py + 14, 58, 72), border_radius=10)
                    pygame.draw.rect(self.screen, (98, 108, 134), (px + 30, py + 26, 12, 12), border_radius=3)
                    pygame.draw.rect(self.screen, (98, 108, 134), (px + 46, py + 26, 12, 12), border_radius=3)
                    pygame.draw.rect(self.screen, (98, 108, 134), (px + 30, py + 46, 12, 12), border_radius=3)
                    pygame.draw.rect(self.screen, (98, 108, 134), (px + 46, py + 46, 12, 12), border_radius=3)
                elif item == "tree":
                    pygame.draw.rect(self.screen, (92, 74, 44), (px + 50, py + 42, 10, 28))
                    pygame.draw.circle(self.screen, (44, 104, 70), (px + 55, py + 30), 18)
                elif item == "streetlight":
                    pygame.draw.line(self.screen, (160, 160, 170), (px + 58, py + 72), (px + 58, py + 12), 4)
                    pygame.draw.line(self.screen, (160, 160, 170), (px + 58, py + 18), (px + 78, py + 28), 4)
                    pygame.draw.circle(self.screen, (248, 227, 140), (px + 80, py + 28), 7)
                elif item == "car":
                    car_rect = pygame.Rect(px + 14, py + 30, 68, 28)
                    pygame.draw.rect(self.screen, (82, 90, 98), car_rect, border_radius=8)
                    pygame.draw.circle(self.screen, (28, 28, 32), car_rect.midleft, 7)
                    pygame.draw.circle(self.screen, (28, 28, 32), car_rect.midright, 7)
                    pygame.draw.rect(self.screen, (116, 132, 158), (px + 26, py + 34, 32, 14), border_radius=6)
                else:
                    pygame.draw.rect(self.screen, (80, 86, 96), (px + 18, py + 38, 56, 20), border_radius=4)
                    pygame.draw.circle(self.screen, (52, 56, 64), (px + 28, py + 52), 7)
                    pygame.draw.circle(self.screen, (52, 56, 64), (px + 64, py + 52), 7)

    def _draw_level_result_overlay(self) -> None:
        if not self.level_result_open or self.level_result is None:
            return
        if self.level_result_close_rect is None:
            return

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((7, 10, 18, 190))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(SCREEN_WIDTH // 2 - 310, SCREEN_HEIGHT // 2 - 220, 620, 440)
        pygame.draw.rect(self.screen, (24, 29, 43), panel, border_radius=16)
        pygame.draw.rect(self.screen, (118, 143, 196), panel, 2, border_radius=16)

        close_rect = pygame.Rect(panel.right - 38, panel.y + 10, 24, 24)
        self.level_result_close_rect = close_rect
        pygame.draw.rect(self.screen, (88, 92, 110), close_rect, border_radius=6)
        pygame.draw.line(self.screen, TEXT, (close_rect.left + 6, close_rect.top + 6), (close_rect.right - 6, close_rect.bottom - 6), 2)
        pygame.draw.line(self.screen, TEXT, (close_rect.left + 6, close_rect.bottom - 6), (close_rect.right - 6, close_rect.top + 6), 2)

        success = bool(self.level_result["success"])
        title_text = "УРОВЕНЬ ПРОЙДЕН" if success else "УРОВЕНЬ ПРОВАЛЕН"
        title_color = SUCCESS if success else DANGER
        title = self.big_font.render(title_text, True, title_color)
        self.screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 18))

        close_rect = self.level_result_close_rect
        pygame.draw.rect(self.screen, (88, 92, 110), close_rect, border_radius=6)
        pygame.draw.line(self.screen, TEXT, (close_rect.left + 6, close_rect.top + 6), (close_rect.right - 6, close_rect.bottom - 6), 2)
        pygame.draw.line(self.screen, TEXT, (close_rect.left + 6, close_rect.bottom - 6), (close_rect.right - 6, close_rect.top + 6), 2)

        level_name = self.font.render(str(self.level_result["level_name"]), True, TEXT)
        self.screen.blit(level_name, (panel.centerx - level_name.get_width() // 2, panel.y + 78))

        stars = cast(int, self.level_result["stars"])
        stars_txt = self.font.render(f"Рейтинг: {self._star_text(stars)}", True, ACCENT)
        self.screen.blit(stars_txt, (panel.centerx - stars_txt.get_width() // 2, panel.y + 120))

        result_lines = [
            f"Время: {self._formatted_time(cast(float, self.level_result['time']))}",
            f"Получен урон: {cast(int, self.level_result['damage'])}",
            f"Убийства: {cast(int, self.level_result['kills'])}",
            f"Скор: {cast(float, self.level_result['score']):.1f}",
        ]
        y = panel.y + 168
        for line in result_lines:
            text = self.font.render(line, True, TEXT)
            self.screen.blit(text, (panel.centerx - text.get_width() // 2, y))
            y += 32

        best = self.best_results.get(str(self.current_level_index), {})
        best_stars = int(best.get("best_stars", 0)) if isinstance(best, dict) else 0
        best_time = float(best.get("best_time", 0.0)) if isinstance(best, dict) else 0.0
        best_line = f"Лучший результат: {self._star_text(best_stars)}  {self._formatted_time(best_time)}"
        best_text = self.font.render(best_line, True, ACCENT)
        self.screen.blit(best_text, (panel.centerx - best_text.get_width() // 2, panel.y + 300))

        hint = "Нажмите ЛКМ по кнопке ниже"
        hint_text = self.small_font.render(hint, True, (190, 198, 214))
        self.screen.blit(hint_text, (panel.centerx - hint_text.get_width() // 2, panel.y + 332))

        next_button = pygame.Rect(panel.centerx - 230, panel.y + 360, 220, 52)
        retry_button = pygame.Rect(panel.centerx + 10, panel.y + 360, 220, 52)
        self.level_result_buttons = {
            "next": next_button,
            "retry": retry_button,
        }

        next_label = "Следующий уровень" if success and self.current_level_index < len(LEVELS) - 1 else "Сыграть снова"
        next_color = (58, 108, 77) if success else (96, 87, 58)
        pygame.draw.rect(self.screen, next_color, next_button, border_radius=10)
        pygame.draw.rect(self.screen, (143, 213, 169), next_button, 2, border_radius=10)
        next_txt = self.small_font.render(next_label, True, TEXT)
        self.screen.blit(next_txt, (next_button.centerx - next_txt.get_width() // 2, next_button.y + 15))

        pygame.draw.rect(self.screen, (118, 72, 72), retry_button, border_radius=10)
        pygame.draw.rect(self.screen, (245, 134, 134), retry_button, 2, border_radius=10)
        retry_txt = self.small_font.render("Повторить уровень", True, TEXT)
        self.screen.blit(retry_txt, (retry_button.centerx - retry_txt.get_width() // 2, retry_button.y + 15))

    def _draw_end_overlay(self) -> None:
        if not self.game_over and not self.victory:
            return

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((4, 8, 14, 155))
        self.screen.blit(overlay, (0, 0))

        label = "ПОБЕДА" if self.victory else "ПОРАЖЕНИЕ"
        color = SUCCESS if self.victory else DANGER
        text = self.big_font.render(label, True, color)
        self.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 210))

        summary = f"Пройдено волн: {self.wave_number}/{self.current_level.waves}    Убийств: {self.total_kills}"
        hint = "Нажмите R для перезапуска"
        s1 = self.font.render(summary, True, TEXT)
        s2 = self.font.render(hint, True, TEXT)
        self.screen.blit(s1, (SCREEN_WIDTH // 2 - s1.get_width() // 2, 286))
        self.screen.blit(s2, (SCREEN_WIDTH // 2 - s2.get_width() // 2, 324))

    def draw(self) -> None:
        self._draw_background()
        self._draw_path()
        self._draw_grid()
        self._draw_obstacles()
        self._draw_towers()
        self._draw_enemies()
        self._draw_projectiles()
        self._draw_menu_button()
        self._draw_sidebar()
        self._draw_end_overlay()
        self._draw_level_result_overlay()
        self._draw_settings_overlay()
        self._draw_menu_overlay()
        self._draw_level_select_overlay()
        self._draw_info_modal()
        self._present()

    def run(self) -> None:
        while True:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)

                if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    if self.game_over or self.victory or self.level_result_open:
                        self._restart_current_level()

                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if self.settings_open or self.level_select_open or self.level_result_open:
                        self.open_menu()
                    elif not self.menu_open:
                        self.open_menu()

                if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self._toggle_fullscreen()

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mouse_world = self._screen_to_world_pos(event.pos)
                    if self.level_result_open:
                        if (
                            self.level_result_close_rect is not None
                            and self.level_result_close_rect.collidepoint(*mouse_world)
                        ):
                            self.open_menu()
                            continue
                        next_button = self.level_result_buttons.get("next") if hasattr(self, "level_result_buttons") else None
                        retry_button = self.level_result_buttons.get("retry") if hasattr(self, "level_result_buttons") else None
                        if next_button and next_button.collidepoint(*mouse_world):
                            self._advance_level()
                            continue
                        if retry_button and retry_button.collidepoint(*mouse_world):
                            self._restart_current_level()
                            continue

                    self._handle_click(*mouse_world)

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                    mouse_world = self._screen_to_world_pos(event.pos)
                    if not self._handle_right_click(*mouse_world):
                        self.selected_tower_type = None

            self.update(dt)
            self.draw()


def run() -> None:
    Game().run()
