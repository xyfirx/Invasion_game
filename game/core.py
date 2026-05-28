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
    LEVELS,
    OBSTACLE_NAMES,
    SIDEBAR_WIDTH,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SUCCESS,
    TEXT,
    TOWER_DESCRIPTIONS,
    TOWER_TYPES,
    LevelStats,
    TowerStats,
)
from .entities import Enemy, Projectile, Tower, distance_sq
from .input import handle_click, handle_level_result_click, handle_right_click
from .logic import build_obstacles, build_path_tiles, place_tower, remove_obstacle, register_enemy_kill, spawn_enemy, start_wave, choose_target, target_angle, apply_hit
from .save_manager import load_save_data, save_save_data
from .ui import draw as render_frame
from .utils import formatted_time, result_score, star_for_result


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
            self.stars.append([
                random.uniform(0, FIELD_WIDTH),
                random.uniform(0, FIELD_HEIGHT),
                random.uniform(12, 38),
                random.uniform(1.0, 2.7),
            ])

        self.buttons: list[dict] = []
        self.menu_buttons: dict[str, pygame.Rect] = {}
        self.level_select_buttons: dict[str, pygame.Rect] = {}
        self.settings_buttons: dict[str, pygame.Rect] = {}
        self.level_result_buttons: dict[str, pygame.Rect] = {}
        self._create_ui_buttons()
        self.reset_round(0)

    def _load_save_data(self) -> dict[str, dict[str, float | int]]:
        return load_save_data(self.save_path)

    def _save_save_data(self) -> None:
        save_save_data(self.save_path, self.best_results)

    def reset_round(self, level_index: int | None = None) -> None:
        if level_index is not None:
            self.current_level_index = max(0, min(level_index, len(LEVELS) - 1))

        self.current_level = LEVELS[self.current_level_index]
        self.path_cells = list(self.current_level.path_cells)
        self.path_tiles = build_path_tiles(self.path_cells)
        self.waypoints = [
            (col * CELL_SIZE + CELL_SIZE / 2, row * CELL_SIZE + CELL_SIZE / 2)
            for col, row in self.path_cells
        ]
        self.obstacles = build_obstacles(self)

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
        self.level_result_buttons = {}
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

    def _open_info_modal(self, kind: str, value: str, obstacle: dict[str, object] | None = None) -> None:
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
            self.buttons.append({"kind": "tower", "tower_key": tower_key, "rect": pygame.Rect(x, y, w, h)})
            y += h + gap

        self.buttons.append({"kind": "wave", "rect": pygame.Rect(x, y + 20, w, 62)})

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

        self.menu_buttons = {
            "start": pygame.Rect(center_x - 180, center_y - 72, 360, 60),
            "levels": pygame.Rect(center_x - 180, center_y + 4, 360, 60),
            "settings": pygame.Rect(center_x - 180, center_y + 80, 360, 60),
            "exit": pygame.Rect(center_x - 180, center_y + 156, 360, 60),
        }

        self.level_select_buttons = {
            "level_0": pygame.Rect(center_x - 230, center_y - 40, 460, 64),
            "level_1": pygame.Rect(center_x - 230, center_y + 40, 460, 64),
            "level_2": pygame.Rect(center_x - 230, center_y + 120, 460, 64),
            "back": pygame.Rect(center_x - 230, center_y + 210, 220, 56),
            "start": pygame.Rect(center_x + 10, center_y + 210, 220, 56),
        }

    def _toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            desktop_width, desktop_height = pygame.display.get_desktop_sizes()[0]
            self.display = pygame.display.set_mode((desktop_width, desktop_height), pygame.FULLSCREEN)
        else:
            self.display = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.display_size = self.display.get_size()

    def _formatted_time(self, seconds: float) -> str:
        return formatted_time(seconds)

    def _ui_overlay_open(self) -> bool:
        return self.menu_open or self.level_select_open or self.settings_open or self.level_result_open

    def _trigger_level_result(self, success: bool) -> None:
        stars = star_for_result(self.current_level, self.elapsed_time, self.damage_taken, success)
        score = result_score(self.elapsed_time, self.damage_taken)
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

    def _update_best_result(self, level_index: int, result: dict[str, object]) -> None:
        key = str(level_index)
        current = self.best_results.get(key)
        new_score = float(result["score"])

        if current is None or new_score < float(current.get("best_score", 10**9)):
            self.best_results[key] = {
                "best_stars": int(result["stars"]),
                "best_score": new_score,
                "best_time": float(result["time"]),
                "best_damage": int(result["damage"]),
            }
            self._save_save_data()
        else:
            best_stars = int(current.get("best_stars", 0))
            if int(result["stars"]) > best_stars:
                current["best_stars"] = int(result["stars"])
                self._save_save_data()

    def _screen_to_world_pos(self, pos: tuple[int, int]) -> tuple[float, float]:
        if not self.fullscreen:
            return float(pos[0]), float(pos[1])
        display_w, display_h = self.display_size
        if display_w == 0 or display_h == 0:
            return float(pos[0]), float(pos[1])
        scale_x = SCREEN_WIDTH / display_w
        scale_y = SCREEN_HEIGHT / display_h
        return pos[0] * scale_x, pos[1] * scale_y

    def _update_stars(self, dt: float) -> None:
        for star in self.stars:
            star[1] = (star[1] + star[3] * dt) % FIELD_HEIGHT

    def _advance_level(self) -> None:
        next_index = self.current_level_index + 1
        if next_index >= len(LEVELS):
            self.open_menu()
            return
        self.start_game(next_index)

    def _restart_current_level(self) -> None:
        self.reset_round(self.current_level_index)

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
                spawn_enemy(self)
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

            target = choose_target(tower, self.enemies)
            if target is None:
                continue

            tower.aim_angle = target_angle(tower, target)
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
                    apply_hit(projectile.target, projectile.stats, projectile.damage, self.enemies, lambda enemy: register_enemy_kill(self, enemy))
                to_remove.append(projectile)

        for projectile in to_remove:
            if projectile in self.projectiles:
                self.projectiles.remove(projectile)

        self.enemies = [enemy for enemy in self.enemies if enemy.alive]

        if self.in_wave and self.wave_spawned >= self.wave_to_spawn and not self.enemies:
            self.in_wave = False
            self._trigger_level_result(success=True)

        if self.lives <= 0:
            self.game_over = True
            self._trigger_level_result(success=False)

    def _draw_background(self) -> None:
        pass

    def draw(self) -> None:
        render_frame(self)
        self.display.blit(self.screen, (0, 0))
        pygame.display.flip()

    def run(self) -> None:
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    if self.game_over or self.victory or self.level_result_open:
                        self.reset_round(self.current_level_index)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if self.settings_open or self.level_select_open or self.level_result_open:
                        self.open_menu()
                    elif not self.menu_open:
                        self.open_menu()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self._toggle_fullscreen()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mouse_world = self._screen_to_world_pos(event.pos)
                    if self.level_result_open and handle_level_result_click(self, *mouse_world):
                        continue
                    handle_click(self, *mouse_world)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                    mouse_world = self._screen_to_world_pos(event.pos)
                    if not handle_right_click(self, *mouse_world):
                        self.selected_tower_type = None
            self.update(dt)
            self.draw()


def run() -> None:
    Game().run()
