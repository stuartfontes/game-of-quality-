import json

import pygame

from src.core import settings
from src.core.screen import Screen
from src.core.ui import draw_text, draw_text_centered


class HubScreen(Screen):
    def __init__(self, manager):
        super().__init__(manager)
        with open(settings.DATA_DIR / "hub.json", encoding="utf-8") as f:
            self.data = json.load(f)

        assets = manager.assets
        self.font_title = assets.font(settings.FONT_FILE, settings.FONT_SIZE_TITLE)
        self.font_body = assets.font(settings.FONT_FILE, settings.FONT_SIZE_BODY)
        self.font_small = assets.font(settings.FONT_FILE, settings.FONT_SIZE_SMALL)

        self.games = self.data["games"]
        self.index = 0

        margin = 16
        count = len(self.games)
        card_w = (settings.INTERNAL_WIDTH - margin * (count + 1)) // count
        card_h = 112
        top = 72
        self.cards = [
            pygame.Rect(margin + i * (card_w + margin), top, card_w, card_h)
            for i in range(count)
        ]

    def on_enter(self):
        self.index = 0

    def update(self, dt):
        inputs = self.manager.input
        if inputs.pressed("left"):
            self.index = (self.index - 1) % len(self.games)
        if inputs.pressed("right"):
            self.index = (self.index + 1) % len(self.games)
        if inputs.pressed("confirm"):
            self.manager.go_to(self.games[self.index]["id"])

    def draw(self, surface):
        surface.fill(settings.COLOR_BG)
        center_x = settings.INTERNAL_WIDTH // 2

        draw_text_centered(
            surface, self.data["title"], self.font_title,
            settings.COLOR_HIGHLIGHT, center_x, 14,
        )
        draw_text_centered(
            surface, self.data["subtitle"], self.font_body,
            settings.COLOR_TEXT, center_x, 44,
        )

        for i, (game, rect) in enumerate(zip(self.games, self.cards)):
            selected = i == self.index
            card = rect.move(0, -4) if selected else rect
            border = settings.COLOR_HIGHLIGHT if selected else settings.COLOR_DIM
            title_color = settings.COLOR_HIGHLIGHT if selected else settings.COLOR_TEXT

            pygame.draw.rect(surface, settings.COLOR_PANEL, card)
            pygame.draw.rect(surface, border, card, 2)
            draw_text_centered(
                surface, game["title"], self.font_body,
                title_color, card.centerx, card.y + 10,
            )
            draw_text(
                surface, game["description"], self.font_small,
                settings.COLOR_TEXT, (card.x + 8, card.y + 36), card.width - 16,
            )

        draw_text_centered(
            surface, self.data["hint"], self.font_small,
            settings.COLOR_DIM, center_x, settings.INTERNAL_HEIGHT - 20,
        )