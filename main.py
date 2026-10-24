import pygame

from src.core import settings
from src.core.assets import Assets
from src.core.game_state import GameState
from src.core.input_manager import InputManager
from src.core.screen_manager import ScreenManager
from src.screens.hub import HubScreen
from src.screens.placeholder import PlaceholderGameScreen


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

    manager.register("hub", HubScreen(manager))
    manager.register(
        "plataforma",
        PlaceholderGameScreen(manager, "plataforma", "Caminho da Qualidade"),
    )
    manager.register(
        "receita",
        PlaceholderGameScreen(manager, "receita", "Monte o Processo"),
    )
    manager.home_screen = "hub"
    manager.go_to("hub")

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