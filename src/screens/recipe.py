import json
import random

import pygame

from src.core import settings
from src.core.screen import Screen
from src.core.ui import MessageBox, draw_text_centered


class RecipeScreen(Screen):
    def __init__(self, manager):
        super().__init__(manager)
        with open(settings.DATA_DIR / "recipe.json", encoding="utf-8") as f:
            data = json.load(f)
        self.title = data["title"]
        self.steps = data["steps"]

        assets = manager.assets
        self.font_title = assets.font(settings.FONT_FILE, settings.FONT_SIZE_BODY)
        self.font = assets.font(settings.FONT_FILE, settings.FONT_SIZE_SMALL)
        self.row_h = self.font.get_linesize() + 4
        self.box = MessageBox((16, 96, 352, 108), self.font)

        self.pool = []
        self.placed = 0
        self.cursor = 0
        self.finished = False

    def on_enter(self):
        self.manager.state.start_run("receita")
        self.pool = list(range(len(self.steps)))
        while len(self.pool) > 1 and self.pool == sorted(self.pool):
            random.shuffle(self.pool)
        self.placed = 0
        self.cursor = 0
        self.finished = False
        self.box.hide()

    def update(self, dt):
        self.box.update(dt)
        inputs = self.manager.input

        if self.box.visible:
            if inputs.pressed("confirm"):
                if self.finished:
                    self.manager.go_to("hub")
                else:
                    self.box.hide()
            return

        if not self.pool:
            return

        if inputs.pressed("up"):
            self.cursor = (self.cursor - 1) % len(self.pool)
        if inputs.pressed("down"):
            self.cursor = (self.cursor + 1) % len(self.pool)
        if inputs.pressed("confirm"):
            self.pick()

    def pick(self):
        state = self.manager.state
        chosen = self.pool[self.cursor]

        if chosen == self.placed:
            self.pool.pop(self.cursor)
            self.placed += 1
            self.cursor = max(0, min(self.cursor, len(self.pool) - 1))
            if self.placed == len(self.steps):
                state.win()
                self.finished = True
                text = state.messages["victory"] + "\n" + state.messages["voucher"]
                self.box.show(text, title="Parabéns")
            return

        message = state.lose_life()
        text = message + "\n" + self.steps[chosen]["error"]
        self.box.show(text, title="Etapa fora de ordem")
        if state.game_over:
            self.finished = True

    def draw_lives(self, surface):
        state = self.manager.state
        size = 8
        gap = 4
        total = settings.MAX_ATTEMPTS
        x = settings.INTERNAL_WIDTH - 8 - total * (size + gap)
        for i in range(total):
            rect = pygame.Rect(x + i * (size + gap), 8, size, size)
            if i < state.lives:
                pygame.draw.rect(surface, settings.COLOR_ERROR, rect)
            else:
                pygame.draw.rect(surface, settings.COLOR_DIM, rect, 1)

    def draw(self, surface):
        surface.fill(settings.COLOR_BG)
        draw_text_centered(
            surface, self.title, self.font_title,
            settings.COLOR_HIGHLIGHT, settings.INTERNAL_WIDTH // 2, 6,
        )
        self.draw_lives(surface)

        top = 48
        left_x = 12
        right_x = 204
        count = len(self.steps)

        surface.blit(self.font.render("Etapas", False, settings.COLOR_DIM), (left_x, top - 16))
        surface.blit(self.font.render("Processo", False, settings.COLOR_DIM), (right_x, top - 16))
        pygame.draw.line(
            surface, settings.COLOR_DIM,
            (198, top), (198, top + count * self.row_h),
        )

        for row, idx in enumerate(self.pool):
            selected = row == self.cursor
            color = settings.COLOR_HIGHLIGHT if selected else settings.COLOR_TEXT
            prefix = "> " if selected else "  "
            label = self.font.render(prefix + self.steps[idx]["name"], False, color)
            surface.blit(label, (left_x, top + row * self.row_h))

        for slot in range(count):
            if slot < self.placed:
                text = f"{slot + 1}. {self.steps[slot]['name']}"
                color = settings.COLOR_SUCCESS
            elif slot == self.placed:
                text = f"{slot + 1}. ?"
                color = settings.COLOR_HIGHLIGHT
            else:
                text = f"{slot + 1}. -"
                color = settings.COLOR_DIM
            surface.blit(self.font.render(text, False, color), (right_x, top + slot * self.row_h))

        self.box.draw(surface)