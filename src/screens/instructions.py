import json

from src.core import settings
from src.core.screen import Screen
from src.core.ui import draw_text, draw_text_centered


class InstructionsScreen(Screen):
    def __init__(self, manager, game_id):
        super().__init__(manager)
        self.game_id = game_id
        with open(settings.DATA_DIR / "instructions.json", encoding="utf-8") as f:
            self.data = json.load(f)[game_id]

        assets = manager.assets
        self.font_title = assets.font(settings.FONT_FILE, settings.FONT_SIZE_BODY)
        self.font_body = assets.font(settings.FONT_FILE, settings.FONT_SIZE_SMALL)
        self.elapsed = 0.0

    def on_enter(self):
        self.elapsed = 0.0

    def update(self, dt):
        self.elapsed += dt
        inputs = self.manager.input
        if inputs.pressed("back"):
            self.manager.go_to("hub")
        elif inputs.pressed("confirm"):
            self.manager.go_to(self.game_id)

    def draw(self, surface):
        surface.fill(settings.COLOR_BG)
        center_x = settings.INTERNAL_WIDTH // 2

        draw_text_centered(
            surface, self.data["title"], self.font_title,
            settings.COLOR_HIGHLIGHT, center_x, 12,
        )

        y = 44
        for line in self.data["lines"]:
            used = draw_text(
                surface, line, self.font_body, settings.COLOR_TEXT,
                (24, y), settings.INTERNAL_WIDTH - 48,
            )
            y += used + 6

        draw_text_centered(
            surface, self.data["controls"], self.font_body,
            settings.COLOR_DIM, center_x, settings.INTERNAL_HEIGHT - 46,
        )

        if int(self.elapsed * 2) % 2 == 0:
            draw_text_centered(
                surface, "ENTER para começar", self.font_body,
                settings.COLOR_HIGHLIGHT, center_x, settings.INTERNAL_HEIGHT - 28,
            )