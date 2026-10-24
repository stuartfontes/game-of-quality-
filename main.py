import pygame

from src.core import settings
from src.core.input_manager import InputManager
from src.core.screen_manager import ScreenManager
from src.screens.test_screens import TestScreen
from src.core.assets import Assets
from src.screens.ui_test import UITestScreen
from src.core.game_state import GameState


def main():
    pygame.init()

    flags = pygame.FULLSCREEN | pygame.SCALED
    screen = pygame.display.set_mode(
        (settings.INTERNAL_WIDTH, settings.INTERNAL_HEIGHT),
        flags,
        vsync=1,
    )
    pygame.display.set_caption(settings.WINDOW_TITLE)
    pygame.mouse.set_visible(False)

    inputs = InputManager()
    assets = Assets()
    state = GameState()
    manager = ScreenManager(inputs, assets, state)
    manager.register("a", TestScreen(manager, (30, 60, 120), "Tela A - Enter para ir à B", "b"))
    manager.register("b", TestScreen(manager, (100, 40, 60), "Tela B - Enter para ir à A", "a"))
    manager.register("ui", UITestScreen(manager))
    manager.home_screen = "a"
    manager.go_to("ui")

    clock = pygame.time.Clock()

    while manager.running:
        dt = clock.tick(settings.FPS) / 1000

        inputs.begin_frame(dt)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                manager.quit()
            inputs.process(event)
            manager.handle_event(event)

        if inputs.pressed("quit"):
            manager.quit()

        manager.check_idle()

        manager.update(dt)
        manager.draw(screen)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()