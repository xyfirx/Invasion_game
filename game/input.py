from __future__ import annotations

import sys
import pygame

from .logic import place_tower, remove_obstacle, start_wave


def handle_click(game: "Game", mx: float, my: float) -> None:
    if not game._ui_overlay_open() and game.menu_button_rect.collidepoint(mx, my):
        game.open_menu()
        return

    if game.menu_open:
        if game.menu_close_rect and game.menu_close_rect.collidepoint(mx, my):
            game.menu_open = False
            return
        if game.menu_buttons["start"].collidepoint(mx, my):
            game.start_game(game.menu_selected_level)
            return
        if game.menu_buttons["levels"].collidepoint(mx, my):
            game.menu_open = False
            game.level_select_open = True
            return
        if game.menu_buttons["settings"].collidepoint(mx, my):
            game.menu_open = False
            game.settings_open = True
            return
        if game.menu_buttons["exit"].collidepoint(mx, my):
            pygame.quit()
            sys.exit(0)
            return
        return

    if game.level_select_open:
        if game.level_select_close_rect is not None and game.level_select_close_rect.collidepoint(mx, my):
            game.level_select_open = False
            game.menu_open = True
            return
        if game.level_select_buttons["level_0"].collidepoint(mx, my):
            game.menu_selected_level = 0
            return
        if game.level_select_buttons["level_1"].collidepoint(mx, my):
            game.menu_selected_level = 1
            return
        if game.level_select_buttons["level_2"].collidepoint(mx, my):
            game.menu_selected_level = 2
            return
        if game.level_select_buttons["back"].collidepoint(mx, my):
            game.level_select_open = False
            game.menu_open = True
            return
        if game.level_select_buttons["start"].collidepoint(mx, my):
            game.start_game(game.menu_selected_level)
            return
        return

    if game.settings_open:
        if game.settings_close_rect is not None and game.settings_close_rect.collidepoint(mx, my):
            game.settings_open = False
            game.menu_open = True
            return
        if game.settings_buttons["fullscreen"].collidepoint(mx, my):
            game._toggle_fullscreen()
            return
        if game.settings_buttons["back"].collidepoint(mx, my):
            game.settings_open = False
            game.menu_open = True
            return
        return

    if game.info_modal_open:
        if game.info_modal_close_rect and game.info_modal_close_rect.collidepoint(mx, my):
            game._close_info_modal()
            return
        if (
            game.info_modal_action_rect is not None
            and game.info_modal_action_rect.collidepoint(mx, my)
            and game.info_modal_kind == "obstacle"
            and game.info_modal_obstacle is not None
        ):
            remove_obstacle(game, game.info_modal_obstacle)
            game._close_info_modal()
            return
        return

    if 0 <= mx < game.FIELD_WIDTH and 0 <= my < game.FIELD_HEIGHT:
        col = int(mx // game.CELL_SIZE)
        row = int(my // game.CELL_SIZE)
        obstacle = None
        for obstacle_item in game.obstacles:
            if obstacle_item["col"] == col and obstacle_item["row"] == row:
                obstacle = obstacle_item
                break
        if obstacle is not None:
            game._open_info_modal("obstacle", str(obstacle["type"]), obstacle)
            return

    for button in game.buttons:
        rect = button["rect"]
        if not rect.collidepoint(mx, my):
            continue
        if button["kind"] == "tower":
            game.selected_tower_type = button["tower_key"]
            return
        if button["kind"] == "wave":
            start_wave(game)
            return

    place_tower(game, mx, my)


def handle_level_result_click(game: "Game", mx: float, my: float) -> bool:
    if game.level_result_close_rect is not None and game.level_result_close_rect.collidepoint(mx, my):
        game.open_menu()
        return True

    next_button = game.level_result_buttons.get("next") if hasattr(game, "level_result_buttons") else None
    retry_button = game.level_result_buttons.get("retry") if hasattr(game, "level_result_buttons") else None
    if next_button and next_button.collidepoint(mx, my):
        game._advance_level()
        return True
    if retry_button and retry_button.collidepoint(mx, my):
        game._restart_current_level()
        return True
    return False


def handle_right_click(game: "Game", mx: float, my: float) -> bool:
    for button in game.buttons:
        if button["kind"] != "tower":
            continue
        rect = button["rect"]
        if rect.collidepoint(mx, my):
            game.selected_tower_type = button["tower_key"]
            game._open_info_modal("tower", str(button["tower_key"]))
            return True
    return False
