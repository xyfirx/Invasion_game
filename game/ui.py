from __future__ import annotations

import pygame
from typing import cast

from .constants import (
    ACCENT,
    BG_BOTTOM,
    BG_TOP,
    CELL_SIZE,
    DANGER,
    FIELD_HEIGHT,
    FIELD_WIDTH,
    FIELD_GRID,
    GRID_COLS,
    GRID_ROWS,
    LEVELS,
    OBSTACLE_NAMES,
    PATH_COLOR,
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


def _draw_background(game: "Game") -> None:
    game.screen.fill(BG_BOTTOM)
    for y in range(0, FIELD_HEIGHT, CELL_SIZE):
        pygame.draw.line(game.screen, (72, 78, 101), (0, y), (FIELD_WIDTH, y), 1)
    for x in range(0, FIELD_WIDTH, CELL_SIZE):
        pygame.draw.line(game.screen, (72, 78, 101), (x, 0), (x, FIELD_HEIGHT), 1)

    for star in game.stars:
        pygame.draw.circle(game.screen, (157, 172, 209), (int(star[0]), int(star[1])), int(max(1, star[2] * 0.15)))

    for col, row in game.path_cells:
        rect = pygame.Rect(col * CELL_SIZE, row * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(game.screen, PATH_COLOR, rect)

    for obstacle in game.obstacles:
        pygame.draw.rect(game.screen, (102, 91, 69), obstacle["rect"])


def _draw_sidebar(game: "Game") -> None:
    pygame.draw.rect(game.screen, (22, 27, 44), (FIELD_WIDTH, 0, SIDEBAR_WIDTH, SCREEN_HEIGHT))
    title = game.font.render("Управление", True, TEXT)
    game.screen.blit(title, (FIELD_WIDTH + 18, 18))

    for button in game.buttons:
        rect = button["rect"]
        color = ACCENT if button["kind"] == "wave" else (68, 88, 132)
        pygame.draw.rect(game.screen, color, rect)
        label = "Старт волны" if button["kind"] == "wave" else TOWER_TYPES[button["tower_key"]].name
        text = game.small_font.render(label, True, TEXT)
        game.screen.blit(text, (rect.x + 12, rect.y + 16))


def _draw_game_objects(game: "Game") -> None:
    for tower in game.towers:
        pygame.draw.circle(game.screen, tower.stats.color, (int(tower.x), int(tower.y)), 12)
        pygame.draw.circle(game.screen, (255, 255, 255), (int(tower.x), int(tower.y)), 20, 1)

    for enemy in game.enemies:
        pygame.draw.circle(game.screen, enemy.color, (int(enemy.x), int(enemy.y)), int(enemy.radius))
        hp_ratio = max(0.0, min(1.0, enemy.hp / enemy.max_hp if enemy.max_hp else 0.0))
        hp_rect = pygame.Rect(int(enemy.x - enemy.radius), int(enemy.y - enemy.radius - 8), int(enemy.radius * 2 * hp_ratio), 4)
        pygame.draw.rect(game.screen, (122, 244, 146), hp_rect)
        pygame.draw.rect(game.screen, (36, 45, 62), pygame.Rect(int(enemy.x - enemy.radius), int(enemy.y - enemy.radius - 8), int(enemy.radius * 2), 4), 1)

    for projectile in game.projectiles:
        pygame.draw.circle(game.screen, projectile.color, (int(projectile.x), int(projectile.y)), 5)


def _draw_menu(game: "Game") -> None:
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((10, 14, 24, 210))
    game.screen.blit(overlay, (0, 0))

    pygame.draw.rect(game.screen, (18, 23, 38), (120, 100, 720, 420), border_radius=12)
    title = game.big_font.render("Invasion Defense", True, TEXT)
    game.screen.blit(title, (160, 120))

    for name, rect in game.menu_buttons.items():
        pygame.draw.rect(game.screen, (44, 56, 82), rect, border_radius=10)
        text = game.small_font.render(name.capitalize(), True, TEXT)
        game.screen.blit(text, (rect.x + 18, rect.y + 18))


def draw(game: "Game") -> None:
    _draw_background(game)
    _draw_sidebar(game)
    _draw_game_objects(game)

    status_text = game.font.render(f"Уровень: {game.current_level.name}", True, TEXT)
    game.screen.blit(status_text, (FIELD_WIDTH + 18, SCREEN_HEIGHT - 62))

    if game.menu_open or game.level_select_open or game.settings_open or game.level_result_open:
        _draw_menu(game)
