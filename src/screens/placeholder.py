from src.core import settings
from src.core.screen import Screen
from src.core.ui import draw_text_centered


class PlaceholderGameScreen(Screen):
    def __init__(self, manager, game_id, title):
        super().__init__(manager)
        self.game_id = game_id
        self.title = title
        self.font = manager.assets.font(settings.FONT_FILE, settings.FONT_SIZE_BODY)
        self.font_small = manager.assets.font(settings.FONT_FILE, settings.FONT_SIZE_SMALL)

    def on_enter(self):
        self.manager.state.start_run(self.game_id)

    def update(self, dt):
        if self.manager.input.pressed("back"):
            self.manager.go_to("hub")

    def draw(self, surface):
        surface.fill(settings.COLOR_BG)
        center_x = settings.INTERNAL_WIDTH // 2
        middle = settings.INTERNAL_HEIGHT // 2

        draw_text_centered(
            surface, self.title, self.font,
            settings.COLOR_HIGHLIGHT, center_x, middle - 24,
        )
        draw_text_centered(
            surface, "Em construção", self.font_small,
            settings.COLOR_TEXT, center_x, middle,
        )
        draw_text_centered(
            surface, "BACKSPACE voltar", self.font_small,
            settings.COLOR_DIM, center_x, settings.INTERNAL_HEIGHT - 20,
        )