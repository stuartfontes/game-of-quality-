import pygame

from src.core import settings
from src.core.screen_manager import ScreenManager
from src.screens.test_screens import TestScreen


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

    manager = ScreenManager()
    manager.register("a", TestScreen(manager, (30, 60, 120), "Tela A - Enter para ir à B", "b"))
    manager.register("b", TestScreen(manager, (100, 40, 60), "Tela B - Enter para ir à A", "a"))
    manager.go_to("a")

    clock = pygame.time.Clock()

    while manager.running:
        dt = clock.tick(settings.FPS) / 1000

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                manager.quit()
            elif event.type == pygame.KEYDOWN and event.key in settings.KEYMAP["quit"]:
                manager.quit()
            else:
                manager.handle_event(event)

        manager.update(dt)
        manager.draw(screen)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()