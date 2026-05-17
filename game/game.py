from __future__ import annotations

import sys
from pathlib import Path

import pygame

class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Invasion Defense")
        self.display = pygame.display.set_mode((960, 672))

    def run(self) -> None:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)


def run() -> None:
    Game().run()
